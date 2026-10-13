package com.smartkaraoke.ai

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

class AnalysisViewModel : ViewModel() {
    var busy by mutableStateOf(false)
        private set
    var result by mutableStateOf<JSONObject?>(null)
        private set
    var message by mutableStateOf("")
        private set
    var isError by mutableStateOf(false)
        private set
    var fileName by mutableStateOf("")
        private set
    var connectionReady by mutableStateOf<Boolean?>(null)
        private set
    private var analyzedBaseUrl = ""
    private val api = AudioApi()

    fun fileSelected(context: Context, uri: Uri) {
        result = null
        isError = false
        fileName = "File âm thanh"
        message = "Đã chọn bản thu. Nhấn Phân tích giọng hát để nhận hướng dẫn chỉnh vang."
        viewModelScope.launch {
            fileName = withContext(Dispatchers.IO) {
                runCatching {
                    context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                        if (cursor.moveToFirst()) cursor.getString(0) else null
                    }
                }.getOrNull() ?: "File âm thanh"
            }
        }
    }

    fun checkConnection(baseUrl: String) {
        if (busy) return
        busy = true
        isError = false
        connectionReady = null
        message = "Đang kiểm tra kết nối…"
        viewModelScope.launch {
            try {
                api.health(baseUrl)
                connectionReady = true
                message = "Đã kết nối máy tính. Bạn có thể phân tích bản thu."
            } catch (e: CancellationException) { throw e
            } catch (e: Exception) { connectionReady = false; isError = true; message = api.errorMessage(e, baseUrl)
            } finally { busy = false }
        }
    }

    fun analyze(context: Context, uri: Uri, baseUrl: String, room: String, vocalType: String?) {
        if (busy) return
        val rt60 = if (room.isBlank()) null else room.replace(',', '.').toDoubleOrNull()
        if (room.isNotBlank() && (rt60 == null || !rt60.isFinite() || rt60 !in 0.1..5.0)) {
            message = "RT60 phải từ 0.1 đến 5 giây, hoặc để trống."
            isError = true
            return
        }
        busy = true
        isError = false
        result = null
        connectionReady = null
        message = "Đang xử lý bản thu… Lần đầu có thể mất thêm thời gian."
        viewModelScope.launch {
            try {
                message = "Đang kết nối với máy tính…"
                api.health(baseUrl)
                connectionReady = true
                message = "Đang gửi file và phân tích… Lần đầu có thể mất thêm thời gian."
                result = api.analyze(context.applicationContext, uri, baseUrl, rt60, vocalType)
                analyzedBaseUrl = baseUrl
                message = "Đã phân tích."
            } catch (e: CancellationException) { throw e
            } catch (e: Exception) { if (connectionReady == null) connectionReady = false; isError = true; message = api.errorMessage(e, baseUrl)
            } finally { busy = false }
        }
    }

    fun feedback(device: String, rating: Int, notes: String) {
        val id = result?.getString("analysis_id") ?: return
        if (busy) return
        busy = true
        isError = false
        message = "Đang lưu đánh giá…"
        viewModelScope.launch {
            try {
                api.feedback(analyzedBaseUrl, id, device, rating, notes)
                message = "Đã lưu đánh giá."
            } catch (e: CancellationException) { throw e
            } catch (e: Exception) { isError = true; message = api.errorMessage(e, analyzedBaseUrl)
            } finally { busy = false }
        }
    }
}
