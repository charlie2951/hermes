import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.colors import LogNorm, SymLogNorm


class PlotterVisualGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TCAD-2D Visual  |  Device & Multi-Curve I-V Analyzer")
        self.root.geometry("1380x840")
        self.root.configure(bg="#f5f6f8")

        # Multi-curve I-V storage: list of dicts {"name": str, "df": DataFrame, "var": BooleanVar}
        self.iv_datasets = []
        self.vtk_data = None
        self.cutline_mode = tk.StringVar(value="Horizontal (X-Cut)")
        self.cutline_pos = None
        self.toolbar_vtk = None

        # Persistent 2D plot artists
        self.cbar_vtk = None
        self.cutline_line = None
        self._current_Z_plot = None
        self._current_use_log = False

        self._setup_styles()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if os.path.exists("iv_output.csv"):
            self.load_csv("iv_output.csv")
        if os.path.exists("device_final.vtk"):
            self.load_vtk("device_final.vtk")

    def on_close(self):
        plt.close("all")
        self.root.quit()
        self.root.destroy()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f6f8")
        style.configure("TLabelframe", background="#f5f6f8", foreground="#1f2328")
        style.configure("TLabelframe.Label", background="#f5f6f8", foreground="#0969da", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#f5f6f8", foreground="#1f2328", font=("Segoe UI", 9))
        style.configure("TButton", background="#0969da", foreground="white", font=("Segoe UI", 9, "bold"), padding=5)
        style.map("TButton", background=[("active", "#0550ae")])
        style.configure("TCheckbutton", background="#f5f6f8", foreground="#1f2328", font=("Segoe UI", 9))
        style.configure("TRadiobutton", background="#f5f6f8", foreground="#1f2328", font=("Segoe UI", 9))
        style.configure("TNotebook", background="#e8eaed", borderwidth=0)
        style.configure("TNotebook.Tab", background="#e1e4e8", foreground="#24292f", padding=[14, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#0969da")])

    def _build_ui(self):
        topbar = ttk.Frame(self.root, padding=6)
        topbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(topbar, text="Add I-V Curve (.csv)", command=self.browse_csv).pack(side=tk.LEFT, padx=4)
        ttk.Button(topbar, text="Load 2D Snapshot (.vtk)", command=self.browse_vtk).pack(side=tk.LEFT, padx=4)
        ttk.Button(topbar, text="Exit", command=self.on_close).pack(side=tk.RIGHT, padx=4)
        self.status_lbl = ttk.Label(topbar, text="Ready. Load CSV or VTK files to inspect.", foreground="#0550ae")
        self.status_lbl.pack(side=tk.RIGHT, padx=12)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.tab_iv = ttk.Frame(self.notebook)
        self.tab_vtk = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_iv, text="  I-V Characteristics & Multi-Curve Overlay  ")
        self.notebook.add(self.tab_vtk, text="  2D Field Viewer & Cutline (VTK)  ")

        self._build_iv_tab()
        self._build_vtk_tab()

    # =========================================================================
    # TAB 1: MULTI-CURVE I-V ANALYZER & METRICS
    # =========================================================================
    def _build_iv_tab(self):
        ctrl = ttk.Frame(self.tab_iv, width=300, padding=8)
        ctrl.pack(side=tk.LEFT, fill=tk.Y)
        ctrl.pack_propagate(False)

        # Loaded CSV Curves List
        ds_box = ttk.LabelFrame(ctrl, text="Loaded I-V Datasets", padding=8)
        ds_box.pack(fill=tk.X, pady=4)
        self.ds_vars_frame = ttk.Frame(ds_box)
        self.ds_vars_frame.pack(fill=tk.X)

        btn_row = ttk.Frame(ds_box)
        btn_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(btn_row, text="+ Add CSV", command=self.browse_csv).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_row, text="Clear All", command=self.clear_iv_datasets).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        # Terminal selection (union of all terminal columns across loaded CSVs)
        term_box = ttk.LabelFrame(ctrl, text="Terminals to Plot", padding=8)
        term_box.pack(fill=tk.X, pady=6)
        self.term_vars_frame = ttk.Frame(term_box)
        self.term_vars_frame.pack(fill=tk.X)
        self.term_check_vars = {}

        # Plot options (gm and Log scale disabled by default)
        opt_box = ttk.LabelFrame(ctrl, text="Plot Options", padding=8)
        opt_box.pack(fill=tk.X, pady=6)

        self.iv_abs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_box, text="Plot Absolute Current |I|", variable=self.iv_abs_var,
                        command=self.update_iv_plots).pack(anchor=tk.W)

        self.iv_log_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_box, text="Show Semi-Log Subthreshold Plot", variable=self.iv_log_var,
                        command=self.update_iv_plots).pack(anchor=tk.W, pady=4)

        self.iv_gm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_box, text="Overlay Transconductance (gm)", variable=self.iv_gm_var,
                        command=self.update_iv_plots).pack(anchor=tk.W)

        # Extracted Device Metrics
        met_box = ttk.LabelFrame(ctrl, text="Device Metrics (First Active Curve)", padding=8)
        met_box.pack(fill=tk.X, pady=6)
        self.metrics_lbl = ttk.Label(met_box, text="Load an I-V CSV file to\ncompute Ion, Ioff, SS, gm.",
                                     font=("Consolas", 9), justify=tk.LEFT)
        self.metrics_lbl.pack(anchor=tk.W)

        # Right Canvas
        plot_frame = ttk.Frame(self.tab_iv)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        plt.style.use("default")
        self.fig_iv = plt.figure(figsize=(10, 5.5), facecolor="#ffffff")
        self.canvas_iv = FigureCanvasTkAgg(self.fig_iv, master=plot_frame)
        self.canvas_iv.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(self.canvas_iv, plot_frame)
        toolbar.update()

    # =========================================================================
    # TAB 2: 2D VTK VIEWER WITH INTERACTIVE CUTLINE
    # =========================================================================
    def _build_vtk_tab(self):
        ctrl = ttk.Frame(self.tab_vtk, width=300, padding=8)
        ctrl.pack(side=tk.LEFT, fill=tk.Y)
        ctrl.pack_propagate(False)

        fld_box = ttk.LabelFrame(ctrl, text="Scalar Field", padding=8)
        fld_box.pack(fill=tk.X, pady=5)

        ttk.Label(fld_box, text="Quantity:").pack(anchor=tk.W)
        self.vtk_field_var = tk.StringVar()
        self.vtk_field_combo = ttk.Combobox(fld_box, textvariable=self.vtk_field_var, state="readonly")
        self.vtk_field_combo.pack(fill=tk.X, pady=4)
        self.vtk_field_combo.bind("<<ComboboxSelected>>", lambda e: self.render_2d_field(reset_zoom=True))

        ttk.Label(fld_box, text="Colormap:").pack(anchor=tk.W, pady=(6, 0))
        self.cmap_var = tk.StringVar(value="jet")
        cmap_combo = ttk.Combobox(fld_box, textvariable=self.cmap_var, state="readonly",
                                  values=["jet", "viridis", "inferno", "plasma", "coolwarm", "magma"])
        cmap_combo.pack(fill=tk.X, pady=4)
        cmap_combo.bind("<<ComboboxSelected>>", lambda e: self.render_2d_field(reset_zoom=False))

        self.vtk_log_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fld_box, text="Log Scale (2D & Cutline)", variable=self.vtk_log_var,
                        command=lambda: self.render_2d_field(reset_zoom=False)).pack(anchor=tk.W, pady=4)

        self.show_mesh_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(fld_box, text="Show FVM Grid Lines", variable=self.show_mesh_var,
                        command=lambda: self.render_2d_field(reset_zoom=False)).pack(anchor=tk.W, pady=2)

        cut_box = ttk.LabelFrame(ctrl, text="1D Cutline Tool", padding=8)
        cut_box.pack(fill=tk.X, pady=8)

        ttk.Radiobutton(cut_box, text="Horizontal (X-Cut at Y)", variable=self.cutline_mode,
                        value="Horizontal (X-Cut)", command=self._reset_cutline_slider).pack(anchor=tk.W)
        ttk.Radiobutton(cut_box, text="Vertical (Y-Cut at X)", variable=self.cutline_mode,
                        value="Vertical (Y-Cut)", command=self._reset_cutline_slider).pack(anchor=tk.W)

        self.cut_coord_lbl = ttk.Label(cut_box, text="Position: -- nm", foreground="#cf222e", font=("Segoe UI", 9, "bold"))
        self.cut_coord_lbl.pack(anchor=tk.W, pady=(8, 2))

        self.cut_slider = ttk.Scale(cut_box, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                                    command=self._on_slider_move)
        self.cut_slider.pack(fill=tk.X, pady=4)

        ttk.Label(cut_box, text="Tip: Left-click on the 2D plot to move\nthe cutline without resizing.",
                  foreground="#57606a", font=("Segoe UI", 8, "italic")).pack(anchor=tk.W, pady=4)

        ttk.Button(cut_box, text="Reset 2D View", command=lambda: self.render_2d_field(reset_zoom=True)).pack(fill=tk.X, pady=(4, 2))
        ttk.Button(cut_box, text="Export Cutline CSV", command=self.export_cutline_csv).pack(fill=tk.X, pady=4)

        probe_box = ttk.LabelFrame(ctrl, text="Cursor Probe", padding=8)
        probe_box.pack(fill=tk.X, pady=5)
        self.probe_lbl = ttk.Label(probe_box, text="X: -- nm\nY: -- nm\nValue: --", font=("Consolas", 9))
        self.probe_lbl.pack(anchor=tk.W)

        plot_frame = ttk.Frame(self.tab_vtk)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig_vtk = plt.figure(figsize=(9.5, 7), facecolor="#ffffff")
        gs = self.fig_vtk.add_gridspec(2, 2, width_ratios=[40, 1.3], height_ratios=[1.35, 1.0],
                                       left=0.09, right=0.92, top=0.93, bottom=0.08,
                                       hspace=0.35, wspace=0.05)
        self.ax_2d = self.fig_vtk.add_subplot(gs[0, 0])
        self.cax_2d = self.fig_vtk.add_subplot(gs[0, 1])
        self.ax_cut = self.fig_vtk.add_subplot(gs[1, 0])

        self.canvas_vtk = FigureCanvasTkAgg(self.fig_vtk, master=plot_frame)
        self.canvas_vtk.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.toolbar_vtk = NavigationToolbar2Tk(self.canvas_vtk, plot_frame)
        self.toolbar_vtk.update()

        self.canvas_vtk.mpl_connect("button_press_event", self._on_2d_click)
        self.canvas_vtk.mpl_connect("motion_notify_event", self._on_2d_hover)

    # =========================================================================
    # MULTI-CSV LOADING & MANAGEMENT
    # =========================================================================
    def browse_csv(self):
        paths = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if paths:
            for p in paths:
                self.load_csv(p)
            self.notebook.select(self.tab_iv)

    def clear_iv_datasets(self):
        self.iv_datasets.clear()
        for w in self.ds_vars_frame.winfo_children():
            w.destroy()
        for w in self.term_vars_frame.winfo_children():
            w.destroy()
        self.term_check_vars.clear()
        self.fig_iv.clear()
        self.canvas_iv.draw()
        self.metrics_lbl.config(text="Load an I-V CSV file to\ncompute Ion, Ioff, SS, gm.")
        self.status_lbl.config(text="Cleared all I-V datasets.")

    def load_csv(self, path):
        try:
            df = pd.read_csv(path)
            base_name = os.path.splitext(os.path.basename(path))[0]

            # Ensure unique display label if same filename is loaded from different folders
            existing_names = {d["name"] for d in self.iv_datasets}
            label = base_name
            counter = 2
            while label in existing_names:
                label = f"{base_name}_{counter}"
                counter += 1

            ds_var = tk.BooleanVar(value=True)
            self.iv_datasets.append({"name": label, "df": df, "var": ds_var})
            ttk.Checkbutton(self.ds_vars_frame, text=label, variable=ds_var,
                            command=self.update_iv_plots).pack(anchor=tk.W)

            # Register any new terminal columns into the Terminals checkbox panel
            current_cols = [c for c in df.columns if c != "V_sweep"]
            """
            for idx, col in enumerate(current_cols):
                if col not in self.term_check_vars:
                    default_on = ("DRAIN" in col.upper() or "ANODE" in col.upper() or (len(self.term_check_vars) == 0 and idx == 0))
                    var = tk.BooleanVar(value=default_on)
                    self.term_check_vars[col] = var
                    ttk.Checkbutton(self.term_vars_frame, text=col, variable=var,
                                    command=self.update_iv_plots).pack(anchor=tk.W)
            """
            # Register any new terminal columns into the Terminals checkbox panel
            current_cols = [c for c in df.columns if c != "V_sweep"]
            primary_cols = [
                c for c in current_cols
                if any(k in c.upper() for k in ("DRAIN", "ANODE", "COLLECTOR"))
            ]
            fallback_cols = [
                c for c in current_cols
                if not any(k in c.upper() for k in ("GATE", "SUB", "BULK", "SOURCE", "CATHODE", "EMITTER"))
            ]

            for col in current_cols:
                if col not in self.term_check_vars:
                    if primary_cols:
                        default_on = (col == primary_cols[0])
                    elif fallback_cols:
                        default_on = (col == fallback_cols[0])
                    else:
                        default_on = False

                    var = tk.BooleanVar(value=default_on)
                    self.term_check_vars[col] = var
                    ttk.Checkbutton(self.term_vars_frame, text=col, variable=var,
                                    command=self.update_iv_plots).pack(anchor=tk.W)

            self.status_lbl.config(text=f"Loaded {len(self.iv_datasets)} I-V curve(s)")
            self.update_iv_plots()
        except Exception as exc:
            messagebox.showerror("CSV Load Error", str(exc))

    # =========================================================================
    # MULTI-CURVE I-V PLOTTING & METRIC EXTRACTION
    # =========================================================================
    def update_iv_plots(self):
        self.fig_iv.clear()
        active_datasets = [d for d in self.iv_datasets if d["var"].get()]
        selected_cols = [col for col, var in self.term_check_vars.items() if var.get()]

        if not active_datasets or not selected_cols:
            self.canvas_iv.draw()
            return

        show_log = self.iv_log_var.get()
        if show_log:
            ax_lin = self.fig_iv.add_subplot(1, 2, 1)
            ax_log = self.fig_iv.add_subplot(1, 2, 2)
            self.fig_iv.subplots_adjust(left=0.08, right=0.92, top=0.90, bottom=0.12, wspace=0.32)
        else:
            ax_lin = self.fig_iv.add_subplot(1, 1, 1)
            ax_log = None
            self.fig_iv.subplots_adjust(left=0.09, right=0.93, top=0.90, bottom=0.12)

        colors = ["#0969da", "#cf222e", "#1a7f37", "#8250df", "#bf8700", "#0550ae", "#d1242f"]
        markers = ["o", "s", "^", "D", "v", "P", "X"]

        primary_v = None
        primary_i = None
        primary_label = None
        curve_idx = 0

        ax_gm = ax_lin.twinx() if self.iv_gm_var.get() else None

        for ds in active_datasets:
            df = ds["df"]
            v = df["V_sweep"].values
            for col in selected_cols:
                if col not in df.columns:
                    continue
                curr = df[col].values
                y_vals = np.abs(curr) if self.iv_abs_var.get() else curr
                c = colors[curve_idx % len(colors)]
                m = markers[curve_idx % len(markers)]

                # Include dataset name if multiple datasets are loaded
                legend_lbl = f"{ds['name']} ({col})" if len(self.iv_datasets) > 1 else col

                if primary_i is None:
                    primary_v = v
                    primary_i = np.abs(curr)
                    primary_label = legend_lbl

                ax_lin.plot(v, y_vals, marker=m, markersize=4, lw=2.0, color=c, label=legend_lbl)

                if show_log and ax_log is not None:
                    ax_log.semilogy(v, np.maximum(np.abs(curr), 1e-20), marker=m, markersize=4, lw=2.0, color=c, label=legend_lbl)

                if ax_gm is not None and len(v) >= 3:
                    gm = np.gradient(np.abs(curr), v)
                    ax_gm.plot(v, gm, linestyle="--", lw=1.4, color=c, alpha=0.75, label=f"gm: {legend_lbl}")

                curve_idx += 1

        ax_lin.set_title("I-V Characteristics (Linear Scale)", fontsize=11, fontweight="bold", color="#1f2328")
        ax_lin.set_xlabel("Sweep Voltage (V)", fontsize=10)
        ax_lin.set_ylabel("Current ($\\mu$A/$\\mu$m)", fontsize=10)
        ax_lin.grid(True, linestyle=":", alpha=0.55, color="#b0b8c1")
        ax_lin.legend(loc="upper left", fontsize=8.5, framealpha=0.92)

        if ax_gm is not None:
            ax_gm.set_ylabel("Transconductance gm ($\\mu$S/$\\mu$m)", color="#cf222e", fontsize=9.5)
            ax_gm.tick_params(axis="y", colors="#cf222e")

        if show_log and ax_log is not None:
            ax_log.set_title("Subthreshold / Semi-Log I-V", fontsize=11, fontweight="bold", color="#1f2328")
            ax_log.set_xlabel("Sweep Voltage (V)", fontsize=10)
            ax_log.set_ylabel("|Current| ($\\mu$A/$\\mu$m)", fontsize=10)
            ax_log.grid(True, which="both", linestyle=":", alpha=0.55, color="#b0b8c1")
            ax_log.legend(loc="lower right", fontsize=8.5, framealpha=0.92)

        # Compute device metrics for the first active curve
        if primary_i is not None and len(primary_v) >= 2:
            i_off = float(primary_i[0])
            i_on = float(primary_i[-1])
            ratio = (i_on / i_off) if i_off > 0 else np.inf
            gm_arr = np.gradient(primary_i, primary_v)
            idx_gm_max = int(np.argmax(gm_arr))
            gm_max = float(gm_arr[idx_gm_max])
            # Linear Extrapolation Vth at peak gm: Vth = V(gm_max) - I(gm_max) / gm_max
            if gm_max > 0.0:
                v_at_gm = float(primary_v[idx_gm_max])
                i_at_gm = float(primary_i[idx_gm_max])
                v_th = v_at_gm - (i_at_gm / gm_max)
            else:
                v_th = np.nan

            log_i = np.log10(np.maximum(primary_i, 1e-22))
            dlogi_dv = np.gradient(log_i, primary_v)
            valid = dlogi_dv > 1e-3
            ss_mv_dec = float(np.min(1000.0 / dlogi_dv[valid])) if np.any(valid) else np.nan

            self.metrics_lbl.config(
                text=(
                    f"Curve   : {primary_label}\n"
                    f"V_th    : {v_th:.3f} V\n"
                    f"I_off   : {i_off:.3e} uA/um\n"
                    f"I_on    : {i_on:.3e} uA/um\n"
                    f"Ion/Ioff: {ratio:.2e}\n"
                    f"Peak gm : {gm_max:.3e} uS/um\n"
                    f"Min SS  : {ss_mv_dec:.1f} mV/dec"
                )
            )

        self.canvas_iv.draw()

    # =========================================================================
    # VTK LOADING & ZERO-RESIZE CUTLINE ENGINE
    # =========================================================================
    def browse_vtk(self):
        path = filedialog.askopenfilename(filetypes=[("VTK files", "*.vtk"), ("All files", "*.*")])
        if path:
            self.load_vtk(path)
            self.notebook.select(self.tab_vtk)

    def load_vtk(self, path):
        try:
            with open(path, "r") as f:
                lines = [line.strip() for line in f if line.strip()]

            nx = ny = 0
            points = []
            fields = {}
            i = 0
            while i < len(lines):
                parts = lines[i].split()
                if parts[0] == "DIMENSIONS":
                    nx, ny = int(parts[1]), int(parts[2])
                elif parts[0] == "POINTS":
                    n_pts = int(parts[1])
                    for k in range(1, n_pts + 1):
                        xyz = lines[i + k].split()
                        points.append((float(xyz[0]) * 1e7, float(xyz[1]) * 1e7))
                    i += n_pts
                elif parts[0] == "POINT_DATA":
                    n_pts = int(parts[1])
                    i += 1
                    while i < len(lines):
                        header = lines[i].split()
                        if header[0] == "SCALARS":
                            fname = header[1]
                            i += 2
                            vals = [float(lines[i + k]) for k in range(n_pts)]
                            fields[fname] = np.array(vals).reshape((ny, nx))
                            i += n_pts
                        else:
                            i += 1
                    break
                i += 1

            pts_arr = np.array(points).reshape((ny, nx, 2))
            self.vtk_data = {
                "nx": nx,
                "ny": ny,
                "x": pts_arr[0, :, 0],
                "y": pts_arr[:, 0, 1],
                "fields": fields,
            }

            field_names = list(fields.keys())
            self.vtk_field_combo["values"] = field_names
            if "ElectronDensity" in field_names:
                self.vtk_field_var.set("ElectronDensity")
            elif field_names:
                self.vtk_field_var.set(field_names[0])

            ymin, ymax = float(self.vtk_data["y"].min()), float(self.vtk_data["y"].max())
            self.cut_slider.configure(from_=ymin, to=ymax)
            self.cutline_pos = 0.5 * (ymin + ymax)
            self.cut_slider.set(self.cutline_pos)

            self.status_lbl.config(text=f"Loaded VTK: {os.path.basename(path)} ({nx}x{ny} grid)")
            self.render_2d_field(reset_zoom=True)
        except Exception as exc:
            messagebox.showerror("VTK Load Error", str(exc))

    def render_2d_field(self, reset_zoom=True):
        if not self.vtk_data:
            return
        fname = self.vtk_field_var.get()
        if fname not in self.vtk_data["fields"]:
            return

        x = self.vtk_data["x"]
        y = self.vtk_data["y"]
        Z = self.vtk_data["fields"][fname]
        X, Y = np.meshgrid(x, y)

        has_prev = (not reset_zoom) and (self.cutline_line is not None)
        if has_prev:
            prev_xlim = self.ax_2d.get_xlim()
            prev_ylim = self.ax_2d.get_ylim()

        self.ax_2d.clear()
        self.cax_2d.clear()

        use_log = self.vtk_log_var.get() and ("Potential" not in fname and "ElectricField" not in fname)
        norm = None
        Z_plot = Z.copy()
        if use_log:
            if np.any(Z_plot < 0):
                linthresh = max(1e10, np.max(np.abs(Z_plot)) * 1e-6)
                norm = SymLogNorm(linthresh=linthresh, vmin=Z_plot.min(), vmax=Z_plot.max())
            else:
                Z_plot = np.maximum(Z_plot, 1.0)
                vmax = max(Z_plot.max(), 10.0)
                vmin = max(Z_plot.min(), 1.0)
                if vmin >= vmax:
                    vmin = vmax * 0.1
                norm = LogNorm(vmin=vmin, vmax=vmax)

        self._current_Z_plot = Z_plot
        self._current_use_log = use_log

        mesh = self.ax_2d.pcolormesh(X, Y, Z_plot, shading="auto", cmap=self.cmap_var.get(), norm=norm)
        self.cbar_vtk = self.fig_vtk.colorbar(mesh, cax=self.cax_2d)
        self.cbar_vtk.set_label(fname, fontsize=9)

        if self.show_mesh_var.get():
            for xv in x:
                self.ax_2d.axvline(xv, color="black", alpha=0.18, lw=0.5)
            for yv in y:
                self.ax_2d.axhline(yv, color="black", alpha=0.18, lw=0.5)

        (self.cutline_line,) = self.ax_2d.plot([], [], color="#111111", linestyle="--", linewidth=1.8)

        if has_prev:
            self.ax_2d.set_xlim(prev_xlim)
            self.ax_2d.set_ylim(prev_ylim)
        else:
            self.ax_2d.set_xlim(x.min(), x.max())
            self.ax_2d.set_ylim(y.max(), y.min())

        self.ax_2d.set_ylabel("Y Depth (nm)", fontsize=9)
        self.ax_2d.set_xlabel("X Position (nm)", fontsize=9)
        self.ax_2d.set_title(f"2D Contour: {fname}", fontsize=11, fontweight="bold", color="#1f2328")

        self.update_cutline_only()

    def update_cutline_only(self):
        if not self.vtk_data or self.cutline_line is None:
            return
        fname = self.vtk_field_var.get()
        x = self.vtk_data["x"]
        y = self.vtk_data["y"]
        Z = self.vtk_data["fields"][fname]
        Z_plot = self._current_Z_plot
        use_log = self._current_use_log

        self.ax_cut.clear()

        is_horiz = self.cutline_mode.get().startswith("Horizontal")
        if is_horiz:
            iy = int(np.argmin(np.abs(y - self.cutline_pos)))
            actual_y = y[iy]
            self.cut_coord_lbl.config(text=f"Y-Cutline: {actual_y:.2f} nm (row {iy})")
            self.cutline_line.set_data([x.min(), x.max()], [actual_y, actual_y])

            slice_vals = Z_plot[iy, :] if use_log else Z[iy, :]
            self.ax_cut.plot(x, slice_vals, color="#0969da", lw=2.0, marker="o", markersize=3)
            self.ax_cut.set_xlim(x.min(), x.max())
            self.ax_cut.set_xlabel("X Position (nm)", fontsize=9)
            self.ax_cut.set_title(f"1D Horizontal Cutline along X at Y = {actual_y:.2f} nm",
                                  fontsize=10, color="#0969da", fontweight="bold")
        else:
            ix = int(np.argmin(np.abs(x - self.cutline_pos)))
            actual_x = x[ix]
            self.cut_coord_lbl.config(text=f"X-Cutline: {actual_x:.2f} nm (col {ix})")
            self.cutline_line.set_data([actual_x, actual_x], [y.min(), y.max()])

            slice_vals = Z_plot[:, ix] if use_log else Z[:, ix]
            self.ax_cut.plot(y, slice_vals, color="#0969da", lw=2.0, marker="o", markersize=3)
            self.ax_cut.set_xlim(y.min(), y.max())
            self.ax_cut.set_xlabel("Y Depth (nm)", fontsize=9)
            self.ax_cut.set_title(f"1D Vertical Cutline along Y at X = {actual_x:.2f} nm",
                                  fontsize=10, color="#0969da", fontweight="bold")

        if use_log and not np.any(Z < 0):
            self.ax_cut.set_yscale("log")
        elif use_log and np.any(Z < 0):
            self.ax_cut.set_yscale("symlog", linthresh=1e10)

        self.ax_cut.set_ylabel(fname, fontsize=9)
        self.ax_cut.grid(True, linestyle=":", alpha=0.5, color="#b0b8c1")
        self.canvas_vtk.draw_idle()

    def _reset_cutline_slider(self):
        if not self.vtk_data:
            return
        if self.cutline_mode.get().startswith("Horizontal"):
            ymin, ymax = float(self.vtk_data["y"].min()), float(self.vtk_data["y"].max())
            self.cut_slider.configure(from_=ymin, to=ymax)
            self.cutline_pos = 0.5 * (ymin + ymax)
        else:
            xmin, xmax = float(self.vtk_data["x"].min()), float(self.vtk_data["x"].max())
            self.cut_slider.configure(from_=xmin, to=xmax)
            self.cutline_pos = 0.5 * (xmin + xmax)
        self.cut_slider.set(self.cutline_pos)
        self.update_cutline_only()

    def _on_slider_move(self, val):
        if not self.vtk_data:
            return
        self.cutline_pos = float(val)
        self.update_cutline_only()

    def _on_2d_click(self, event):
        if not self.vtk_data or event.inaxes != self.ax_2d or event.button != 1:
            return
        if self.toolbar_vtk and getattr(self.toolbar_vtk, "mode", "") != "":
            return
        if event.xdata is None or event.ydata is None:
            return

        if self.cutline_mode.get().startswith("Horizontal"):
            self.cutline_pos = float(np.clip(event.ydata, self.vtk_data["y"].min(), self.vtk_data["y"].max()))
        else:
            self.cutline_pos = float(np.clip(event.xdata, self.vtk_data["x"].min(), self.vtk_data["x"].max()))

        self.cut_slider.set(self.cutline_pos)
        self.update_cutline_only()

    def _on_2d_hover(self, event):
        if not self.vtk_data or event.inaxes != self.ax_2d:
            return
        if event.xdata is None or event.ydata is None:
            return
        fname = self.vtk_field_var.get()
        if fname not in self.vtk_data["fields"]:
            return
        ix = int(np.argmin(np.abs(self.vtk_data["x"] - event.xdata)))
        iy = int(np.argmin(np.abs(self.vtk_data["y"] - event.ydata)))
        val = self.vtk_data["fields"][fname][iy, ix]
        self.probe_lbl.config(
            text=f"X: {self.vtk_data['x'][ix]:6.2f} nm\nY: {self.vtk_data['y'][iy]:6.2f} nm\nValue: {val:.4e}"
        )

    def export_cutline_csv(self):
        if not self.vtk_data:
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="cutline_data.csv")
        if not save_path:
            return
        x = self.vtk_data["x"]
        y = self.vtk_data["y"]
        is_horiz = self.cutline_mode.get().startswith("Horizontal")
        if is_horiz:
            iy = int(np.argmin(np.abs(y - self.cutline_pos)))
            data = {"X_nm": x}
            for fname, arr in self.vtk_data["fields"].items():
                data[fname] = arr[iy, :]
        else:
            ix = int(np.argmin(np.abs(x - self.cutline_pos)))
            data = {"Y_nm": y}
            for fname, arr in self.vtk_data["fields"].items():
                data[fname] = arr[:, ix]
        pd.DataFrame(data).to_csv(save_path, index=False)
        self.status_lbl.config(text=f"Exported cutline to {os.path.basename(save_path)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PlotterVisualGUI(root)
    root.mainloop()