import os
import subprocess

source_dir = "data/labs"
output_dir = os.path.join(source_dir, "pdfs")
os.makedirs(output_dir, exist_ok=True)

for file in os.listdir(source_dir):
    if file.endswith(".py"):
        input_path = os.path.join(source_dir, file)
        tex_path = input_path.replace(".py", ".tex")
        pdf_path = os.path.join(output_dir, file.replace(".py", ".pdf"))

        print(f"Converting {file} to PDF...")

        try:
            # Step 1: Create .tex from .py using pygmentize
            with open(tex_path, "w") as tex_out:
                subprocess.run([
                    "pygmentize", "-f", "latex", "-O", "full,encoding=utf-8", input_path
                ], stdout=tex_out, check=True)

            # Step 2: Compile to PDF using xelatex (Unicode safe)
            subprocess.run([
                "xelatex", "-interaction=nonstopmode", "-output-directory", output_dir, tex_path
            ], check=True)

            os.remove(tex_path)  # Optional cleanup
            aux_file = tex_path.replace(".tex", ".aux")
            log_file = tex_path.replace(".tex", ".log")
            for f in [aux_file, log_file]:
                try: os.remove(os.path.join(output_dir, os.path.basename(f)))
                except: pass

            print(f"PDF saved to: {pdf_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to convert {file}: {e}")