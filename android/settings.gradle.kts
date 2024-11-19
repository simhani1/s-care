pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://repository.map.naver.com/archive/maven")
        maven { url = uri("https://jitpack.io") }
    }
}

rootProject.name = "scare"
include(":app")
include(":wear")
include(":weather")
include(":notification")
include(":hand-pressure-core")
include(":feature-handtracking")
include(":feature-pressure")
include(":feature-analysis")