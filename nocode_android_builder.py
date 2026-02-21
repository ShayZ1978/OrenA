#!/usr/bin/env python3
"""No-code Android app builder with optional desktop GUI.

Generates an Android Studio Kotlin project that wraps a website in a WebView.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppSpec:
    app_name: str
    package_name: str
    start_url: str


def slugify_app_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return cleaned or "MyApp"


def package_to_path(package_name: str) -> Path:
    return Path(*package_name.split("."))


def validate_package(package_name: str) -> None:
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$", package_name):
        raise ValueError("Invalid package name. Example valid format: com.example.myapp")


def parse_prompt(prompt: str) -> AppSpec:
    """Parse user prompt text.

    Accepted format (case-insensitive keys):
      app name: My App
      package: com.example.myapp
      start url: https://example.com
    """
    values: dict[str, str] = {}
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().lower()] = value.strip()

    app_name = values.get("app name") or values.get("name")
    package_name = values.get("package") or values.get("package name")
    start_url = values.get("start url") or values.get("url")

    if not app_name or not package_name or not start_url:
        raise ValueError(
            "Prompt must include: 'app name:', 'package:' and 'start url:' lines."
        )

    if not start_url.startswith(("http://", "https://")):
        raise ValueError("Start URL must begin with http:// or https://")

    validate_package(package_name)
    return AppSpec(app_name=app_name, package_name=package_name, start_url=start_url)


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_project(base_dir: Path, app_name: str, package_name: str, start_url: str) -> Path:
    validate_package(package_name)
    app_slug = slugify_app_name(app_name)
    project_dir = base_dir / app_slug
    java_path = package_to_path(package_name)

    settings_gradle = f'''pluginManagement {{
    repositories {{
        gradlePluginPortal()
        google()
        mavenCentral()
    }}
}}

dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
        google()
        mavenCentral()
    }}
}}

rootProject.name = "{app_slug}"
include(":app")
'''

    root_build_gradle = '''plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
}
'''

    app_build_gradle = f'''plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}

android {{
    namespace = "{package_name}"
    compileSdk = 34

    defaultConfig {{
        applicationId = "{package_name}"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }}

    buildTypes {{
        release {{
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }}
    }}

    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}

    kotlinOptions {{
        jvmTarget = "17"
    }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
}}
'''

    manifest = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="{app_name}"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.Material3.DayNight.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
'''

    activity_main = '''<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <WebView
        android:id="@+id/webView"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

</FrameLayout>
'''

    main_activity = f'''package {package_name}

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {{
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()
        webView.loadUrl("{start_url}")
    }}

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {{
        if (webView.canGoBack()) {{
            webView.goBack()
        }} else {{
            super.onBackPressed()
        }}
    }}
}}
'''

    strings_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{app_name}</string>
</resources>
'''

    write_file(project_dir / "settings.gradle.kts", settings_gradle)
    write_file(project_dir / "build.gradle.kts", root_build_gradle)
    write_file(
        project_dir / "gradle.properties",
        "org.gradle.jvmargs=-Xmx2048m\nandroid.useAndroidX=true\nkotlin.code.style=official\n",
    )
    write_file(project_dir / "app" / "build.gradle.kts", app_build_gradle)
    write_file(project_dir / "app" / "proguard-rules.pro", "")
    write_file(project_dir / "app" / "src" / "main" / "AndroidManifest.xml", manifest)
    write_file(project_dir / "app" / "src" / "main" / "res" / "layout" / "activity_main.xml", activity_main)
    write_file(project_dir / "app" / "src" / "main" / "res" / "values" / "strings.xml", strings_xml)
    write_file(project_dir / "app" / "src" / "main" / "java" / java_path / "MainActivity.kt", main_activity)

    return project_dir


def export_apk(project_dir: Path, destination: Path | None = None) -> Path:
    """Build debug APK and optionally copy it to a chosen path."""
    gradlew = project_dir / "gradlew"
    if gradlew.exists():
        cmd = [str(gradlew), "assembleDebug"]
    else:
        cmd = ["gradle", "assembleDebug"]

    completed = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "APK build failed. Ensure Android SDK and Gradle are installed.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )

    apk = project_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if not apk.exists():
        raise RuntimeError("Build completed but APK not found at expected path.")

    if destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(apk, destination)
        return destination
    return apk


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("No-Code Android App Builder")
    root.geometry("760x520")

    last_project: dict[str, Path | None] = {"path": None}

    heading = tk.Label(root, text="Describe your app", font=("Arial", 16, "bold"))
    heading.pack(pady=(14, 8))

    hint = tk.Label(
        root,
        text=(
            "Use this format:\n"
            "app name: My Store\n"
            "package: com.example.mystore\n"
            "start url: https://example.com"
        ),
        justify="left",
    )
    hint.pack(anchor="w", padx=14)

    prompt_box = tk.Text(root, height=12, width=88)
    prompt_box.pack(padx=14, pady=10)

    output_var = tk.StringVar(value=str(Path.cwd() / "output"))
    output_frame = tk.Frame(root)
    output_frame.pack(fill="x", padx=14)

    tk.Label(output_frame, text="Project output folder:").pack(side="left")
    tk.Entry(output_frame, textvariable=output_var, width=60).pack(side="left", padx=8)

    def choose_output() -> None:
        chosen = filedialog.askdirectory(initialdir=output_var.get() or str(Path.cwd()))
        if chosen:
            output_var.set(chosen)

    tk.Button(output_frame, text="Browse", command=choose_output).pack(side="left")

    status_var = tk.StringVar(value="Ready")
    tk.Label(root, textvariable=status_var, fg="blue").pack(anchor="w", padx=14, pady=8)

    def on_run() -> None:
        try:
            spec = parse_prompt(prompt_box.get("1.0", "end"))
            project = generate_project(Path(output_var.get()), spec.app_name, spec.package_name, spec.start_url)
            last_project["path"] = project
            status_var.set(f"Project generated: {project}")
            messagebox.showinfo("Success", f"Project generated at:\n{project}")
        except Exception as exc:  # UI handler
            messagebox.showerror("Error", str(exc))

    def on_export_apk() -> None:
        try:
            project = last_project["path"]
            if not project:
                raise ValueError("Run project generation first.")
            default_name = f"{project.name}-debug.apk"
            target = filedialog.asksaveasfilename(
                title="Export APK",
                defaultextension=".apk",
                initialfile=default_name,
                filetypes=[("APK file", "*.apk")],
            )
            if not target:
                return
            apk_path = export_apk(project, Path(target))
            status_var.set(f"APK exported: {apk_path}")
            messagebox.showinfo(
                "APK Exported",
                f"APK created:\n{apk_path}\n\nInstall using adb:\nadb install -r \"{apk_path}\"",
            )
        except Exception as exc:  # UI handler
            messagebox.showerror("Export failed", str(exc))

    buttons = tk.Frame(root)
    buttons.pack(pady=14)
    tk.Button(buttons, text="Run", command=on_run, width=18).pack(side="left", padx=8)
    tk.Button(buttons, text="Export APK", command=on_export_apk, width=18).pack(side="left", padx=8)

    root.mainloop()


def prompt_if_missing(value: str | None, prompt_text: str) -> str:
    if value:
        return value
    return input(prompt_text).strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a no-code Android app project from simple inputs."
    )
    parser.add_argument("--app-name", help="App display name")
    parser.add_argument("--package", dest="package_name", help="Android package name (e.g., com.example.app)")
    parser.add_argument("--start-url", help="Website URL loaded in the app")
    parser.add_argument("--output", default=".", help="Output directory")
    parser.add_argument("--gui", action="store_true", help="Launch desktop GUI builder")
    parser.add_argument("--export-apk", action="store_true", help="Build debug APK after generation (requires Gradle + Android SDK)")
    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return

    app_name = prompt_if_missing(args.app_name, "App name: ")
    package_name = prompt_if_missing(args.package_name, "Package name (e.g. com.example.myapp): ")
    start_url = prompt_if_missing(args.start_url, "Start URL (e.g. https://example.com): ")

    if not start_url.startswith(("http://", "https://")):
        raise SystemExit("Start URL must begin with http:// or https://")

    project_dir = generate_project(Path(args.output), app_name, package_name, start_url)
    print(f"✅ Android project generated at: {project_dir}")

    if args.export_apk:
        apk = export_apk(project_dir)
        print(f"✅ APK exported at: {apk}")


if __name__ == "__main__":
    main()
