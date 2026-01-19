from apk_builder import APKConverter
from PIL import Image
import os

# --- STEP 1: CONFIGURATION ---
# Notice: We don't need to give base.apk or keystore paths anymore!
# The library finds them automatically inside itself.
config = {
    "build_tools_path": r"C:\Program Files\android13\android-14",
    "apktool_path": r"C:\apktool\apktool.jar"
}

# --- HELPER: Create Dummy Images (So the test doesn't crash) ---
def create_dummy_image(filename, color):
    if not os.path.exists(filename):
        print(f"   Creating temporary image: {filename}...")
        img = Image.new('RGB', (500, 500), color=color)
        img.save(filename)

def run_test():
    try:
        print("1. Initializing Janu's Library...")
        converter = APKConverter(**config)
        print("   ✅ Library Loaded Successfully!")

        print("\n2. Preparing Test Images...")
        create_dummy_image("test_icon.png", "red")
        create_dummy_image("test_logo.png", "blue")
        create_dummy_image("test_bg.png", "green")

        print("\n3. Building APK...")
        apk_path = converter.convert(
            url="https://julie-ai-zeta.vercel.app",
            app_name="janujulie",
            icon_path="app_logo.png",
            splash_logo_path="splash_screen.png",
            splash_bg_path="splash_bg.png",
            output_dir="final_output",
            splash_time_sec=3
        )

        print(f"\n🎉 SUCCESS! The library works perfectly.")
        print(f"🚀 APK saved at: {apk_path}")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")

if __name__ == "__main__":
    run_test()