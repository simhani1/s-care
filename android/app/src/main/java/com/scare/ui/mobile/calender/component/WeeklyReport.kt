package com.scare.ui.mobile.calender.component

import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.scare.ui.mobile.common.LocalNavController
import com.scare.ui.theme.DarkNavy
import com.scare.ui.theme.NeonYellow
import com.scare.ui.theme.Typography
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.temporal.WeekFields
import java.util.*

@Composable
fun WeeklyReport(
    selectedDate: LocalDate
) {

    val navController = LocalNavController.current

    // 주차 정보와 날짜 범위 계산
    val (startDay, endDay) = getWeekRangeForDate(selectedDate)

    val borderColor = if (isSystemInDarkTheme()) {
        NeonYellow
    } else {
        DarkNavy
    }

    Box(
        modifier = Modifier
            .fillMaxWidth(0.8f) // 버튼 너비를 80%로 설정 (조정 가능)
            .height(100.dp) // 버튼 높이
            .drawBehind {
                // 상단, 좌측, 우측만 테두리를 그립니다 (하단 제외)
                drawRoundRect(
                    color = borderColor,
                    topLeft = androidx.compose.ui.geometry.Offset(0f, 0f),
                    size = size.copy(height = size.height + 100.dp.toPx()),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx(), 16.dp.toPx()),
                    style = Stroke(width = 1.dp.toPx(), cap = StrokeCap.Round)
                )
            }
            .clickable(onClick = {
                navController?.navigate("report?from=$startDay&to=$endDay")
            }),
        contentAlignment = Alignment.Center // 텍스트 중앙 정렬
    ) {
        Text(
            text = "주간 리포트 보러가기",
            style = Typography.titleLarge.copy( // TextStyle 적용
                fontWeight = FontWeight.Bold // 굵기 변경
            )
        )
    }
}

// 주차 계산 함수
fun getWeekRangeForDate(selectedDate: LocalDate): Pair<String, String> {
    val weekFields = WeekFields.of(Locale.getDefault())

    val startOfWeek = selectedDate.with(weekFields.dayOfWeek(), 1L) // 월요일로 설정
    val endOfWeek = selectedDate.with(weekFields.dayOfWeek(), 7L) // 일요일로 설정

    // 날짜 형식 설정
    val dateFormatter = DateTimeFormatter.ofPattern("yyyyMMdd")

    return Pair(
        startOfWeek.format(dateFormatter), // 시작 날짜
        endOfWeek.format(dateFormatter) // 종료 날짜
    )
}
