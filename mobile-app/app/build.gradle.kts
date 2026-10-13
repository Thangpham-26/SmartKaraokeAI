plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "com.smartkaraoke.ai"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.smartkaraoke.ai"
        minSdk = 24
        targetSdk = 35
        versionCode = 2
        versionName = "0.3.0"
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    // Optional existing debug key allows updating a local test install without clearing app data.
    providers.gradleProperty("smartkaraokeDebugKeystore").orNull?.let {
        signingConfigs.getByName("debug").storeFile = file(it)
    }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.02.01"))
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    val localJUnitDir = providers.gradleProperty("localJUnitDir").orNull
    if (localJUnitDir != null) {
        testImplementation(fileTree(localJUnitDir) { include("junit-*.jar", "hamcrest-core-*.jar") })
    } else {
        testImplementation("junit:junit:4.13.2")
    }
}
