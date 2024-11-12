package com.scare.ui.mobile.viewmodel.walk

import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.wearable.PutDataMapRequest
import com.google.android.gms.wearable.Wearable
import com.scare.TAG
import com.scare.data.walk.datastore.*
import com.scare.data.walk.dto.LocationDTO
import com.scare.data.walk.dto.WalkRequestDTO
import com.scare.data.walk.repository.WalkRepository
import com.scare.repository.heartrate.HeartRateRepository
import com.scare.repository.location.LocationRepository
import com.scare.util.WearableUtils
import com.scare.util.formatDateTimeToSearch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.time.LocalDateTime

class WalkViewModel(
    context: Context,
    private val heartRateRepository: HeartRateRepository,
    private val locationRepository: LocationRepository,
    private val walkRepository: WalkRepository
) : ViewModel() {

    private val dataClient = Wearable.getDataClient(context)

    private val _isWalk = MutableStateFlow(false)
    val isWalk: StateFlow<Boolean> = _isWalk

    private val _walkStartTime = MutableStateFlow("")
    val walkStartTime: StateFlow<String> = _walkStartTime

    private val _walkEndTime = MutableStateFlow("")
    val walkEndTime: StateFlow<String> = _walkEndTime

    private val _heartRates = MutableStateFlow<List<Double>>(emptyList())
    val heartRates: StateFlow<List<Double>> get() = _heartRates

    private val _locations = MutableStateFlow<List<LocationDTO>>(emptyList())
    val locations: StateFlow<List<LocationDTO>> get() = _locations

    private var _locationManager: LocationManager? = null
    private var _locationListener: LocationListener? = null

    init {
        // DataStore에서 산책 상태를 관찰
        viewModelScope.launch {
            getWalkStatus(context).collect { isWalkStatus ->
                _isWalk.value = isWalkStatus
            }
            getWalkStartTime(context).collect { walkStartTime ->
                _walkStartTime.value = walkStartTime
            }
            getWalkEndTime(context).collect { walkEndTime ->
                _walkEndTime.value = walkEndTime
            }
        }
    }

    // 산책 상태 저장
    suspend fun updateWalkStatus(context: Context, isWalk: Boolean) {
        viewModelScope.launch(Dispatchers.IO) {
            saveWalkStatus(context, isWalk)
            _isWalk.value = isWalk

            val isConnected = WearableUtils.isWatchConnected(context)
            if (isConnected) {
                sendToHandheldDevice(isWalk)
            }
        }
    }

    suspend fun updateStartTime(context: Context, startTime: String) {
        viewModelScope.launch(Dispatchers.IO) {
            saveWalkStartTime(context, startTime)
            _walkStartTime.value = startTime
        }
    }

    suspend fun updateEndTime(context: Context, endTime: String) {
        viewModelScope.launch(Dispatchers.IO) {
            saveWalkEndTime(context, endTime)
            _walkEndTime.value = endTime
        }
    }

    private fun sendToHandheldDevice(isWalk: Boolean) {
        val putDataReq = PutDataMapRequest.create("/walkState").apply {
            dataMap.putBoolean("isWalk", isWalk)
            dataMap.putLong("timestamp", System.currentTimeMillis())  // Optional: add a timestamp
        }.asPutDataRequest()
            .setUrgent()

        dataClient.putDataItem(putDataReq).addOnSuccessListener {
            Log.d(TAG, "Walk state is sent to handheld device successfully")
        }.addOnFailureListener { e ->
            Log.e(TAG, "Failed to send walk state to handheld device", e)
        }
    }

    suspend fun fetchHeartRatesWhileWalking(startDate: String, endDate: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val heartRates = heartRateRepository.getHeartRatesWhileWalking(startDate, endDate)
                _heartRates.value = heartRates.map { heartRate -> heartRate.heartRate }
            } catch (e: Exception) {
                Log.e("WalkViewModel", "Error fetching heartrates while walking", e)
            }
        }
    }

    suspend fun fetchLocationsWhileWalking(startDate: String, endDate: String) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val locations = locationRepository.getLocations(startDate, endDate)
                _locations.value = locations.map { location -> LocationDTO(location.latitude, location.longitude) }
            } catch (e: Exception) {
                Log.e("WalkViewModel", "Error fetching locations while walking", e)
            }
        }
    }

    // 위치 업데이트 초기화
    suspend fun startLocationUpdates(context: Context) {
        // LocationManager 초기화
        _locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager

        // LocationListener 정의
        _locationListener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                // 위치가 변경될 때 호출
                locationRepository.save(
                    com.scare.data.location.database.entity.Location(
                        latitude = location.latitude,
                        longitude = location.longitude,
                        createdAt = LocalDateTime.now(),
                    )
                )
            }
        }

        // 위치 업데이트 요청
        try {
            _locationManager?.requestLocationUpdates(
                LocationManager.GPS_PROVIDER, // GPS를 사용
                5000L, // 최소 업데이트 간격 (1초)
                1f, // 최소 거리 변화 (1미터)
                _locationListener!!
            )
        } catch (e: SecurityException) {
            // 위치 권한 예외 처리
            e.printStackTrace()
        }
    }

    // 위치 업데이트 중지
    suspend fun stopLocationUpdates() {
        _locationListener?.let {
            _locationManager?.removeUpdates(it)
        }
        _locationManager = null
        _locationListener = null
    }

    fun handleWalkStart(context: Context) {
        viewModelScope.launch {
            updateWalkStatus(context, true)
            updateStartTime(context, formatDateTimeToSearch(LocalDateTime.now()))
            startLocationUpdates(context)
        }
    }

    fun handleWalkEnd(context: Context) {
        viewModelScope.launch {
            val currentTime = formatDateTimeToSearch(LocalDateTime.now())
            updateWalkStatus(context, false)
            updateEndTime(context, currentTime)
            fetchHeartRatesWhileWalking(_walkStartTime.value, currentTime)
            fetchLocationsWhileWalking(_walkStartTime.value, currentTime)
            stopLocationUpdates()
            postWalking()
        }
    }

    suspend fun postWalking() {
        viewModelScope.launch {
            try {
                if (_locations.value.size < 2 || _heartRates.value.size < 6) {
                    return@launch
                }
                val walk = WalkRequestDTO(_walkStartTime.value, _walkEndTime.value, _heartRates.value, _locations.value)
                walkRepository.postWalk(walk)
            } catch (e: Exception) {
                Log.e("WalkViewModel", "Error posting walk", e)
            }
        }
    }
}
