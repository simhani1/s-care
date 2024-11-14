package com.scare.util

import android.Manifest
import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.scare.R

object LocalNotificationUtil {

    fun showStressNotification(context: Context, title: String, message: String) {
        val channelId = "StressNotification"

        // 알림 채널 생성 (안드로이드 8.0 이상)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "스트레스 지수 경고 알림",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "스트레스 지수가 높을 때마다 알림을 수신합니다. (1시간 주기)"
            }
            val notificationManager = context.getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_stress_notification) // 아이콘 설정
            .setContentTitle("$title - S-care")
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()

        if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            // 권한이 부여된 경우 작업 수행
            NotificationManagerCompat.from(context).notify(1, notification)
        } else {
            // 권한이 없는 경우 요청
            Log.e("stress notification", "권한이 없습니다! 이 부분은 출력되어선 안 됨 (이전에 권한이 체크되어야만 함)")
        }
    }

}
