package com.smartkaraoke.ai

import android.content.Context
import android.net.Uri
import java.net.HttpURLConnection
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.net.URL
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class AudioApi {
    private fun connection(baseUrl: String, path: String, method: String = "POST"): HttpURLConnection {
        val url = URL(baseUrl.trim().trimEnd('/') + path)
        require(url.protocol in listOf("http", "https") && url.host.isNotBlank()) {
            "Địa chỉ API phải bắt đầu bằng http:// hoặc https://"
        }
        return (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 15000
            readTimeout = 180000
            requestMethod = method
            doOutput = method == "POST"
        }
    }

    suspend fun health(baseUrl: String): JSONObject = withContext(Dispatchers.IO) {
        val conn = connection(baseUrl, "/health", "GET")
        conn.connectTimeout = 5000
        conn.readTimeout = 5000
        try {
            response(conn).also { require(it.optString("status") == "ok") { "Máy chủ không phải backend SmartKaraokeAI." } }
        } finally { conn.disconnect() }
    }

    fun errorMessage(error: Exception, baseUrl: String): String = when (error) {
        is SocketTimeoutException -> "Hết thời gian chờ $baseUrl. Kiểm tra địa chỉ backend và kết nối mạng; rồi thử lại."
        is ConnectException, is UnknownHostException ->
            "Không kết nối được $baseUrl. Emulator dùng http://10.0.2.2:8000; điện thoại dùng IP máy tính cùng Wi-Fi. Backend phải đang chạy."
        is SecurityException -> "Không đọc được file đã chọn. Hãy chọn lại file từ bộ nhớ thiết bị."
        else -> error.message ?: "Phân tích thất bại. Hãy kiểm tra kết nối và chọn lại file."
    }

    private fun response(conn: HttpURLConnection): JSONObject {
        val status = conn.responseCode
        val stream = if (status in 200..299) conn.inputStream else conn.errorStream
        val body = stream?.bufferedReader()?.use { it.readText() } ?: ""
        if (status !in 200..299) {
            val detail = when (status) {
                413 -> "File quá lớn, tối đa 20 MiB."
                422 -> "File hoặc dữ liệu không hợp lệ. Dùng WAV/FLAC/OGG/MP4/M4A, 1–60 giây, có âm thanh. " +
                    runCatching { JSONObject(body).opt("detail")?.toString() ?: body }.getOrDefault(body)
                else -> runCatching { JSONObject(body).opt("detail")?.toString() ?: body }.getOrDefault(body)
            }
            error("API $status: ${detail.take(500)}")
        }
        return JSONObject(body)
    }

    suspend fun analyze(context: Context, uri: Uri, baseUrl: String, rt60: Double?, vocalType: String?): JSONObject =
        withContext(Dispatchers.IO) {
            val conn = connection(baseUrl, "/analyze-audio")
            val boundary = "SmartKaraoke-${UUID.randomUUID()}"
            conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            conn.setChunkedStreamingMode(65536)
            try {
                conn.outputStream.use { output ->
                    fun write(value: String) { output.write(value.toByteArray(Charsets.UTF_8)) }
                    if (rt60 != null) {
                        write("--$boundary\r\nContent-Disposition: form-data; name=\"room_rt60_seconds\"\r\n\r\n$rt60\r\n")
                    }
                    if (!vocalType.isNullOrBlank()) {
                        write("--$boundary\r\nContent-Disposition: form-data; name=\"vocal_type\"\r\n\r\n$vocalType\r\n")
                    }
                    write("--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"recording\"\r\nContent-Type: application/octet-stream\r\n\r\n")
                    val input = context.contentResolver.openInputStream(uri)
                        ?: error("Không đọc được file âm thanh")
                    input.use {
                        val buffer = ByteArray(65536)
                        var total = 0L
                        while (true) {
                            val count = it.read(buffer)
                            if (count < 0) break
                            total += count
                            require(total <= 20L * 1024 * 1024) { "File tối đa 20 MiB" }
                            output.write(buffer, 0, count)
                        }
                    }
                    write("\r\n--$boundary--\r\n")
                }
                response(conn)
            } finally { conn.disconnect() }
        }

    suspend fun feedback(baseUrl: String, analysisId: String, device: String, rating: Int, notes: String) =
        withContext(Dispatchers.IO) {
            val conn = connection(baseUrl, "/feedback")
            conn.setRequestProperty("Content-Type", "application/json")
            try {
                val payload = JSONObject().put("analysis_id", analysisId).put("device", device)
                    .put("rating", rating).put("notes", notes)
                conn.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
                response(conn)
            } finally { conn.disconnect() }
        }
}
