package com.smartkaraoke.ai

import java.util.Locale

/** Illustration only: a conventional 270-degree 0–100% scale, not a vendor calibration. */
object DialScale {
    fun percent(value: Double): Float {
        require(value.isFinite()) { "Dial percentage must be finite" }
        return value.coerceIn(0.0, 100.0).toFloat()
    }
    fun angle(value: Double): Float = 135f + percent(value) * 2.7f
    fun label(value: Double): String {
        require(value.isFinite()) { "Parameter must be finite" }
        return if (value % 1.0 == 0.0) value.toInt().toString()
        else String.format(Locale.ROOT, "%.2f", value).trimEnd('0').trimEnd('.').replace('.', ',')
    }
}
