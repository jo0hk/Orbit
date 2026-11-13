package com.example.myapplication

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import java.io.ByteArrayOutputStream
import java.io.File
import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume
fun prepareImageBytes(
    file: File,
    maxSide: Int = 1280,
    maxBytes: Int = 2 * 1024 * 1024
): ByteArray? {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null

    var sample = 1
    while (maxOf(bounds.outWidth, bounds.outHeight) / sample > maxSide * 2) sample *= 2

    var bmp = BitmapFactory.decodeFile(
        file.absolutePath,
        BitmapFactory.Options().apply { inSampleSize = sample }
    ) ?: return null

    // 촬영 방향이 돌아가 있으면 바로잡기
    val orientation = ExifInterface(file.absolutePath)
        .getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
    val degrees = when (orientation) {
        ExifInterface.ORIENTATION_ROTATE_90 -> 90f
        ExifInterface.ORIENTATION_ROTATE_180 -> 180f
        ExifInterface.ORIENTATION_ROTATE_270 -> 270f
        else -> 0f
    }

    // 긴 변 maxSide로 축소
    val ratio = maxSide.toFloat() / maxOf(bmp.width, bmp.height)
    val matrix = Matrix().apply {
        if (ratio < 1f) postScale(ratio, ratio)
        if (degrees != 0f) postRotate(degrees)
    }
    bmp = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, matrix, true)

    // 2MB 이하가 될 때까지 화질을 낮춰가며 압축
    var quality = 90
    var bytes: ByteArray
    do {
        val out = ByteArrayOutputStream()
        bmp.compress(Bitmap.CompressFormat.JPEG, quality, out)
        bytes = out.toByteArray()
        quality -= 10
    } while (bytes.size > maxBytes && quality >= 40)

    return bytes
}
// 촬영 순간에 위치를 한 번만 읽음 (실패하거나 8초 넘으면 null)
@SuppressLint("MissingPermission")
suspend fun getCurrentLatLng(context: Context): Pair<Double, Double>? {
    if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        != PackageManager.PERMISSION_GRANTED
    ) return null

    val client = LocationServices.getFusedLocationProviderClient(context)
    return withTimeoutOrNull(8000L) {
        suspendCancellableCoroutine<Pair<Double, Double>?> { cont ->
            client.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null)
                .addOnSuccessListener { loc ->
                    if (cont.isActive) cont.resume(loc?.let { it.latitude to it.longitude })
                }
                .addOnFailureListener { if (cont.isActive) cont.resume(null) }
        }
    }
}