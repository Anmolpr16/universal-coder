plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }

android { namespace = "com.universalcoder"; compileSdk = 35
    defaultConfig { applicationId = "com.universalcoder"; minSdk = 26; targetSdk = 35; versionCode = 5; versionName = "2.1.0" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
}
