plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.scare"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.scare"
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        vectorDrawables {
            useSupportLibrary = true
        }
        resValue("string", "map_api_key", getApiKey("MAP_API_KEY"))
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.1"
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

fun getApiKey(key: String): String {
    return gradleLocalProperties(rootDir).getProperty(key)
}

dependencies {

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)

    implementation("io.coil-kt:coil-compose:2.0.0")

    implementation("androidx.navigation:navigation-compose:2.8.3")
    implementation(libs.androidx.navigation.runtime.ktx)
    implementation(libs.androidx.work.runtime.ktx)

    implementation("com.naver.maps:map-sdk:3.19.1")
    implementation("io.github.fornewid:naver-map-compose:1.5.1")
    implementation("com.google.android.gms:play-services-location:21.0.1")
    implementation("io.github.fornewid:naver-map-location:21.0.2")

    implementation(platform(libs.firebase.bom)) // Firebase BOM을 사용하여 버전 관리
    implementation(libs.firebase.auth.ktx) // Kotlin 확장 프로그램 사용
    implementation(libs.play.services.auth)
    implementation(libs.androidx.runtime.livedata)

    // Retrofit
    implementation(libs.retrofit)
    implementation(libs.converter.gson) // Gson 변환기

    // OkHttp
    implementation(libs.okhttp)
    implementation(libs.logging.interceptor) // 로깅 인터셉터 (디버깅용)

    //dataStore
    implementation(libs.androidx.datastore.preferences)

    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)
}