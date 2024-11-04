package com.scare.wear

import android.app.Application
import com.scare.wear.data.repository.sensor.HealthServicesRepository
import com.scare.wear.data.repository.sensor.SensorRepository

const val TAG = "scare wear os"
const val PERMISSION = android.Manifest.permission.BODY_SENSORS

class MainApplication : Application() {
    val healthServicesRepository by lazy { HealthServicesRepository(this) }
    val sensorRepository by lazy { SensorRepository(this) }
}
