import os
import json
import shutil
import subprocess
import uuid
import platform
import random
import string
import re
import glob 
from PIL import Image 

class APKConverter:
    # I have added build_tools_path here. This is the fix.
    def __init__(self, 
                 build_tools_path, 
                 apktool_path, 
                 base_apk_path=None,    # Changed to None
                 keystore_path=None,    # Changed to None
                 keystore_pass="123456", 
                 key_alias="mykey"):
        
        self.build_tools_path = build_tools_path
        self.apktool_path = apktool_path
        
        # --- AUTO-DETECT FILES ---
        # Get the folder where THIS file (apk_builder.py) is located
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # If user didn't provide a path, look in the current folder
        if base_apk_path is None:
            self.base_apk_path = os.path.join(current_dir, "base.apk")
        else:
            self.base_apk_path = base_apk_path

        if keystore_path is None:
            self.keystore_path = os.path.join(current_dir, "Debug.keystore")
        else:
            self.keystore_path = keystore_path
            
        self.keystore_pass = keystore_pass
        self.key_alias = key_alias
        
        # Tools setup
        self.zipalign_path = None
        self.apksigner_path = None
        self._verify_tools_exist()


    def _verify_tools_exist(self):
        system = platform.system()
        zipalign = "zipalign.exe" if system == "Windows" else "zipalign"
        apksigner = "apksigner.bat" if system == "Windows" else "apksigner"
        
        self.zipalign_path = os.path.join(self.build_tools_path, zipalign)
        self.apksigner_path = os.path.join(self.build_tools_path, apksigner)

        if not os.path.exists(self.zipalign_path): 
            raise FileNotFoundError(f"Missing {zipalign} at {self.zipalign_path}")
        if not os.path.exists(self.apksigner_path): 
            raise FileNotFoundError(f"Missing {apksigner} at {self.apksigner_path}")
        if not os.path.exists(self.apktool_path): 
            raise FileNotFoundError(f"Missing apktool.jar at {self.apktool_path}")
        if not os.path.exists(self.base_apk_path):
            raise FileNotFoundError(f"Missing base.apk at {self.base_apk_path}")

    def _clean_conflicting_resources(self, directory, resource_name):
        pattern = os.path.join(directory, f"{resource_name}.*")
        files = glob.glob(pattern)
        for f in files:
            try:
                os.remove(f)
            except Exception as e:
                print(f"Warning: Could not delete {f}: {e}")

    def _process_image(self, image_path, directory, resource_name, resize_dim=None):
        self._clean_conflicting_resources(directory, resource_name)
        target_path = os.path.join(directory, f"{resource_name}.png")
        try:
            img = Image.open(image_path)
            img = img.convert("RGBA")
            if resize_dim:
                img = img.resize(resize_dim, Image.Resampling.LANCZOS)
            img.save(target_path, "PNG")
        except Exception as e:
            raise Exception(f"Error processing image {image_path}: {e}")

    def _run_apktool_decode(self, apk_path, output_dir):
        cmd = ["java", "-jar", self.apktool_path, "d", "-f", "--no-src", "-o", output_dir, apk_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def _run_apktool_build(self, source_dir, output_apk):
        cmd = ["java", "-jar", self.apktool_path, "b", "-o", output_apk, source_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Apktool Build Failed: {result.stderr}")

    def _safe_manifest_update(self, decoded_dir, new_package_name):
        manifest_path = os.path.join(decoded_dir, "AndroidManifest.xml")
        if not os.path.exists(manifest_path): return

        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()

        match = re.search(r'package="([^"]+)"', content)
        if match:
            old_package = match.group(1)
            content = re.sub(r'android:name="\.', f'android:name="{old_package}.', content)
            content = content.replace(f'package="{old_package}"', f'package="{new_package_name}"')
            content = content.replace(f'android:authorities="{old_package}', f'android:authorities="{new_package_name}')
        
        if 'android:extractNativeLibs="false"' in content:
            content = content.replace('android:extractNativeLibs="false"', 'android:extractNativeLibs="true"')

        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)

        yml_path = os.path.join(decoded_dir, "apktool.yml")
        if os.path.exists(yml_path):
            with open(yml_path, 'r', encoding='utf-8') as f:
                yml_content = f.read()
            if "renameManifestPackage:" in yml_content:
                yml_content = re.sub(r'(renameManifestPackage:\s*)(.*)', fr'\1{new_package_name}', yml_content)
            else:
                yml_content += f"\nrenameManifestPackage: {new_package_name}\n"
            with open(yml_path, 'w', encoding='utf-8') as f:
                f.write(yml_content)

    def _update_app_name(self, decoded_dir, new_app_name):
        paths = [
            os.path.join(decoded_dir, "res", "values", "strings.xml"),
            os.path.join(decoded_dir, "res", "values-en", "strings.xml")
        ]
        for p in paths:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                pattern = r'(<string[^>]*name="app_name"[^>]*>)(.*?)(</string>)'
                if re.search(pattern, content):
                    new_content = re.sub(pattern, fr'\1{new_app_name}\3', content)
                    with open(p, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    return

    def _zipalign_apk(self, input_apk, output_apk):
        cmd = [self.zipalign_path, "-p", "-f", "-v", "4", input_apk, output_apk]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)

    def _sign_apk(self, apk_path):
        cmd = [
            self.apksigner_path, "sign",
            "--ks", self.keystore_path,
            "--ks-pass", f"pass:{self.keystore_pass}",
            "--key-pass", f"pass:{self.keystore_pass}",
            "--ks-key-alias", self.key_alias,
            apk_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)

    def generate_unique_package(self):
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"com.gen.a{random_str}"

    def convert(self, url, app_name, icon_path, splash_logo_path, splash_bg_path, output_dir, splash_time_sec=3):
        splash_time_ms = int(splash_time_sec) * 1000
        package_name = self.generate_unique_package()
        
        unique_id = str(uuid.uuid4())[:8]
        temp_work_dir = os.path.join(output_dir, "temp_work")
        work_dir = os.path.join(temp_work_dir, unique_id)
        decoded_dir = os.path.join(work_dir, "decoded")
        rebuilt_apk = os.path.join(work_dir, "rebuilt.apk")
        
        final_apk_name = f"{app_name.replace(' ', '_')}_{unique_id}.apk"
        final_apk_path = os.path.join(output_dir, final_apk_name)

        try:
            os.makedirs(decoded_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)

            print(f"Starting conversion for {app_name}...")
            self._run_apktool_decode(self.base_apk_path, decoded_dir)
            self._safe_manifest_update(decoded_dir, package_name)
            self._update_app_name(decoded_dir, app_name)

            drawable_dir = os.path.join(decoded_dir, "res", "drawable")
            os.makedirs(drawable_dir, exist_ok=True)
            self._process_image(icon_path, drawable_dir, "app_icon", resize_dim=(192, 192))
            self._process_image(splash_logo_path, drawable_dir, "splash_logo")
            self._process_image(splash_bg_path, drawable_dir, "splash_bg")

            new_config = {"url": url, "appName": app_name, "splash_time": splash_time_ms}
            config_path = os.path.join(decoded_dir, "assets", "config.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f)

            self._run_apktool_build(decoded_dir, rebuilt_apk)
            self._zipalign_apk(rebuilt_apk, final_apk_path)
            self._sign_apk(final_apk_path)

            print(f"Success! APK saved to: {final_apk_path}")
            return final_apk_path

        except Exception as e:
            print(f"Error during conversion: {e}")
            raise e
        finally:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)