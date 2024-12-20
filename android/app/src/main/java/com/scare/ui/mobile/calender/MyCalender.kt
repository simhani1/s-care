package com.scare.ui.mobile.calender

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.scare.ui.mobile.calender.component.Calender
import com.scare.ui.mobile.calender.component.DayStress
import com.scare.ui.mobile.calender.component.WeeklyReport
import com.scare.ui.mobile.common.LocalNavController
import com.scare.ui.mobile.common.TheHeader
import com.scare.ui.mobile.viewmodel.calender.MonthlyStressViewModel
import com.scare.ui.theme.ScareTheme
import java.time.LocalDate

@Composable
fun MyCalender(
    monthlyStressViewModel: MonthlyStressViewModel
) {
    var selectedDate by remember { mutableStateOf(LocalDate.now()) } // 선택된 날짜
    var selectedStress by remember { mutableStateOf(0) } // 선택된 날짜의 스트레스 상태

    // ViewModel의 stressLevelMap을 구독
    val stressLevelMap by monthlyStressViewModel.stressLevelMap.collectAsState()

    Scaffold(
        topBar = { TheHeader(null, isMainPage = false) }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(innerPadding)
                .padding(16.dp), // 추가로 패딩을 적용,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // 달력에서 선택된 날짜의 스트레스를 받아옴
            Calender(
                modifier = Modifier,
                onDaySelected = { date ->
                    selectedDate = date
                    selectedStress = stressLevelMap[date] ?: 0 // 선택된 날짜의 스트레스 값 가져오기
                },
                monthlyStressViewModel = monthlyStressViewModel
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 선택된 날짜의 스트레스 표시
            DayStress(modifier = Modifier, stress = selectedStress)

            Spacer(modifier = Modifier.height(16.dp))

            WeeklyReport(selectedDate = selectedDate)
        }
    }
}