package com.scare.ui.mobile.main

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.offset
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.scare.R
import com.scare.ui.mobile.login.LoginViewModel
import androidx.compose.runtime.getValue

@Composable
fun StartPage(navController: NavHostController, loginViewModel: LoginViewModel, onSignInClick: () -> Unit) {
    val profileUrl by loginViewModel.profileUrl.collectAsState()

    if (profileUrl != null) {
        navController.navigate("main") {
            popUpTo("start") { inclusive = true }
        }
    }

    Box {
        StartImage(modifier = Modifier.fillMaxSize())

        GoogleLoginButton(
            onClick = onSignInClick,
            modifier = Modifier
                .align(Alignment.Center)
                .offset(y = LocalConfiguration.current.screenHeightDp.dp * 0.25f)
        )
    }
}

@Composable
fun GoogleLoginButton(onClick: () -> Unit, modifier: Modifier) {
    val googleLoginButton = painterResource(R.drawable.google_login);

    Image (
        painter = googleLoginButton,
        contentDescription = "구글 로그인",
        contentScale = ContentScale.Crop, // 이미지 화면 비율에 맞게 자르기
        modifier = modifier.clickable { onClick() } //
    )
}

@Composable
fun StartImage(modifier: Modifier = Modifier) {
    val startImage = painterResource(R.drawable.startpage)

    Image(
        painter = startImage,
        contentDescription = null,
        modifier = modifier,
        contentScale = ContentScale.Crop // 이미지 화면 비율에 맞게 자르기
    )
}