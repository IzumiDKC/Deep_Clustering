"""Execute the review notebook using existing verified results and dependencies."""
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT = Path(__file__).resolve().parents[2]


def main():
    notebook = nbformat.read(ROOT/"archive/notebooks"/"demo_5_algorithms.ipynb", as_version=4)
    setup = next(cell for cell in notebook.cells if cell.cell_type == "code"
                 and "pip" in cell.source and "install" in cell.source)
    setup.source = ("import sys, numpy, pandas\nprint(sys.version)\n"
                    "print('numpy', numpy.__version__, 'pandas', pandas.__version__)\n"
                    "# Môi trường đã có thư viện; xem kết quả đã kiểm chứng.")
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    try:
        NotebookClient(notebook, timeout=180, km=manager,
                       resources={"metadata":{"path":str(ROOT)}}).execute()
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    destination = ROOT/"archive/notebooks"/"demo_5_algorithms_verified.ipynb"
    nbformat.write(notebook, destination)
    print(f"PASS: all review notebook cells executed; outputs saved to {destination}")


if __name__ == "__main__":
    main()
