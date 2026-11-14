package com.scare.ui.mobile.course.component

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.vectorResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.scare.R
import com.scare.data.course.dto.CourseResponseDTO
import com.scare.ui.theme.Typography
import com.scare.util.formatTimeDifference

@Composable
fun CourseDetailInfo(
    modifier: Modifier,
    course: CourseResponseDTO
) {
    Box(modifier = modifier) {
        Row(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(top = 20.dp, end = 20.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(MaterialTheme.colorScheme.tertiary)
                .padding(horizontal = 24.dp, vertical = 8.dp)
        ) {
            Column(
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "총 시간",
                    color = MaterialTheme.colorScheme.background,
                )
                Text(
                    text = formatTimeDifference(
                        course.startedAt,
                        course.finishedAt
                    ),
                    color = MaterialTheme.colorScheme.background,
                    style = Typography.titleLarge.copy(
                        color = MaterialTheme.colorScheme.tertiary, fontWeight = FontWeight.Bold, fontSize = 24.sp
                    )
                )
                Text(
                    text = "내 스트레스",
                    color = MaterialTheme.colorScheme.background
                )
                val pendingMessage = when (course.analysisStatus) {
                    "ANALYZING" -> "조금만 기다려주세요!"
                    "FAILED" -> "분석하지 못했어요"
                    else -> null
                }
                if (pendingMessage != null) {
                    Text(
                        text = pendingMessage,
                        color = MaterialTheme.colorScheme.background,
                        fontWeight = FontWeight.Bold
                    )
                } else Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = (course.maxStress - course.minStress).toInt().toString(),
                        color = MaterialTheme.colorScheme.background,
                        style = Typography.titleLarge.copy(
                            color = MaterialTheme.colorScheme.tertiary,
                            fontWeight = FontWeight.Bold,
                            fontSize = 24.sp
                        )
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Icon(
                        imageVector = ImageVector.vectorResource(R.drawable.arrow_down),
                        contentDescription = "Stress Down",
                        tint = Color.Unspecified
                    )
                }
            }
        }
    }
}