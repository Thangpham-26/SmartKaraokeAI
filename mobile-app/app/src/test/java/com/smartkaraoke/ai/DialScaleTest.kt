package com.smartkaraoke.ai

import org.junit.Assert.*
import org.junit.Test

class DialScaleTest {
    @Test fun percentPointerUsesConsistentMinimumMidpointMaximum() {
        assertEquals(135f, DialScale.angle(0.0), 0.001f)
        assertEquals(270f, DialScale.angle(50.0), 0.001f)
        assertEquals(405f, DialScale.angle(100.0), 0.001f)
        assertEquals(221.4f, DialScale.angle(32.0), 0.001f)
    }
    @Test fun outOfRangePointersCannotWrapAroundTheScale() {
        assertEquals(135f, DialScale.angle(-20.0), 0.001f)
        assertEquals(405f, DialScale.angle(200.0), 0.001f)
    }
    @Test fun nonFiniteValuesAreRejectedInsteadOfDrawingInvalidPointers() {
        for (value in listOf(Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY)) {
            assertThrows(IllegalArgumentException::class.java) { DialScale.angle(value) }
        }
    }
    @Test fun labelsRetainUnitsValuePrecisionWithoutIntegerTruncation() {
        assertEquals("32", DialScale.label(32.0))
        assertEquals("32,45", DialScale.label(32.45))
        assertEquals("-1,5", DialScale.label(-1.5))
    }
}
