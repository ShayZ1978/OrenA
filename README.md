# No-Code Android App Builder

A beginner-friendly tool to generate Android apps without manual Android coding.

## Windows (no terminal use)

### Option A: Double-click launcher (fastest)

1. Open the project folder.
2. Double-click `launch_windows_app.bat`.
3. GUI window opens.

In the window:
- Fill app info
- Click **Run**
- Click **Export APK**

### Option B: Build a real `.exe` app

1. Double-click `build_windows_exe.bat`.
2. Wait for build finish.
3. Your Windows app will be created at:

`dist\NoCodeAndroidBuilder.exe`

Then double-click that `.exe` to open the GUI.

## What you get

- Prompt input window (GUI)
- **Run** button to generate Android project
- **Export APK** button to build and save installable APK (`.apk`)

The generated app is a Kotlin Android project using a `WebView` that opens your URL.

## GUI mode (recommended)

```bash
python3 nocode_android_builder.py --gui
```

In the prompt input window, enter:

```text
app name: My Store
package: com.example.mystore
start url: https://example.com
```

Then:
1. Click **Run**
2. Click **Export APK**
3. Choose where to save the APK file

## CLI mode

```bash
python3 nocode_android_builder.py \
  --app-name "My Store" \
  --package "com.example.mystore" \
  --start-url "https://example.com" \
  --output ./output
```

## Build APK from CLI

```bash
python3 nocode_android_builder.py \
  --app-name "My Store" \
  --package "com.example.mystore" \
  --start-url "https://example.com" \
  --output ./output \
  --export-apk
```

## Install on Android device

```bash
adb install -r /path/to/your.apk
```

## Requirements for APK export

- Gradle available (`gradle` command) or Gradle wrapper (`gradlew`) in generated project
- Android SDK configured (`ANDROID_HOME` / `ANDROID_SDK_ROOT`)

## Tests

```bash
python3 -m unittest discover -s tests -v
```
