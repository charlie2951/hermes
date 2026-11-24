
<h2>HERMES 2D: Web-based Device Simulator — Documentation</h2>
          <p>
            This browser-based 2D Technology Computer-Aided Design (TCAD) simulator solves the coupled Poisson and drift-diffusion equations for 2D semiconductor devices directly inside your browser using WebAssembly.
          </p>

          <img width="540" height="240" alt="image" src="https://github.com/user-attachments/assets/5e3cb361-3f6c-4f7f-8f2c-8862faa1c102" />
          

<h3> 1. Input Deck Syntax Reference</h3>
          <p>All spatial coordinates (<code>X_MIN</code>, <code>X_MAX</code>, <code>Y_MIN</code>, <code>Y_MAX</code>, <code>SIGMA_X</code>, <code>SIGMA_Y</code>) are specified in micrometers (&mu;m).</p>
          <ul>
            <li><code>MESH X_MAX=&lt;val&gt; Y_MAX=&lt;val&gt; NX=&lt;int&gt; NY=&lt;int&gt;</code> — Defines the 2D simulation domain dimensions and tensor-product grid resolution.</li>
            <li><code>REGION MATERIAL=&lt;MAT&gt; X_MIN=&lt;v&gt; X_MAX=&lt;v&gt; Y_MIN=&lt;v&gt; Y_MAX=&lt;v&gt;</code> — Assigns material regions. Supported materials include <code>SILICON</code>, <code>GERMANIUM</code>, <code>OXIDE</code>, and <code>HFO2</code>.</li>
            <li><code>DOPING TYPE=&lt;ACCEPTOR|DONOR&gt; PROFILE=&lt;UNIFORM|GAUSSIAN&gt; CONC=&lt;cm^-3&gt; ...</code> — Adds background or implanted impurity profiles (in cm<sup>&minus;3</sup>). Gaussian profiles accept <code>SIGMA_X</code> and <code>SIGMA_Y</code>.</li>
            <li><code>CONTACT NAME=&lt;ID&gt; TYPE=&lt;OHMIC|SCHOTTKY&gt; [WORKFUNC=&lt;eV&gt;] X_MIN=&lt;v&gt; X_MAX=&lt;v&gt; Y_MIN=&lt;v&gt; Y_MAX=&lt;v&gt;</code> — Places electrical boundary contacts along edges or interfaces.</li>
            <li><code>MODELS SRH=&lt;ON|OFF&gt; FIELD_MOB=&lt;ON|OFF&gt; LOMBARDI=&lt;ON|OFF&gt;</code> — Enables Shockley-Read-Hall recombination, velocity saturation, and surface mobility degradation models. Aso support default parameter overriding by using <code>VSATN=&lt;val&gt;, VSATP=&lt;val&gt;, MUN=&lt;val&gt;, MUP=&lt;val&gt;,TAUN=&lt;val&gt;,TAUP=&lt;val&gt;</code></li>
            <li><code>SOLVE TYPE=&lt;ID_VGS|ID_VDS&gt; SWEEP=&lt;CONTACT&gt; FIXED=&lt;CONTACT&gt; V_START=&lt;V&gt; V_STOP=&lt;V&gt; V_STEP=&lt;V&gt; V_FIXED=&lt;V&gt; OUTFILE=&lt;file.csv&gt;</code> — Runs a quasi-static DC voltage sweep and exports terminal currents in &mu;A/&mu;m.</li>
          </ul>

<h3> 2. Example Input Deck</h3>
          <pre>MESH X_MAX=0.090 Y_MAX=0.022 NX=46 NY=23
REGION MATERIAL=HFO2      X_MIN=0.000 X_MAX=0.090 Y_MIN=0.000 Y_MAX=0.002
REGION MATERIAL=GERMANIUM X_MIN=0.000 X_MAX=0.090 Y_MIN=0.002 Y_MAX=0.012
REGION MATERIAL=OXIDE     X_MIN=0.000 X_MAX=0.090 Y_MIN=0.012 Y_MAX=0.022
DOPING TYPE=ACCEPTOR PROFILE=UNIFORM CONC=1.0e15 X_MIN=0.000 X_MAX=0.090 Y_MIN=0.002 Y_MAX=0.012
CONTACT NAME=GATE TYPE=SCHOTTKY WORKFUNC=4.55 X_MIN=0.030 X_MAX=0.060 Y_MIN=0.000 Y_MAX=0.000
SOLVE TYPE=ID_VGS SWEEP=GATE FIXED=DRAIN V_START=-0.30 V_STOP=0.80 V_STEP=0.05 V_FIXED=0.50 OUTFILE=iv_output.csv</pre>

<h3> 3. Post-Processing &amp; Visualization Guide</h3>
          <ul>
            <li><strong>I-V Results Tab:</strong> Displays terminal drain current versus sweep voltage in Linear or Semilog scale alongside automatically extracted device parameters (Constant-Current V<sub>th</sub> at 0.1 &mu;A/&mu;m, minimum Subthreshold Swing SS, peak transconductance g<sub>m</sub>, I<sub>on</sub>, I<sub>off</sub>, and I<sub>on</sub>/I<sub>off</sub> ratio). Drag the vertical bar between the plot and metrics panel to resize.</li>
            <li><strong>2D VTK &amp; Cutline Tab:</strong> Renders 2D scalar/vector field distributions on the left and a 1D cross-sectional cutline graph on the right. Choose between <em>Auto (Turbo/Viridis)</em>, <em>Turbo</em>, <em>Viridis</em>, and <em>Inferno</em> colormaps, adjust Min/Max color bounds, click anywhere on the 2D device map to move the dashed cutline, and export the active 1D slice via <em>Save Cutline CSV</em>.</li>
            <li><strong>Solver Console:</strong> Monitors real-time Newton-Raphson convergence residuals and solver diagnostics. Drag the horizontal divider above the console to adjust its height.</li>
          </ul>
          <h3 style="color: red;">4. Limitations/Known Issues:</h3>
          <ul>
            <li><strong>One semiconductor region:</strong> This version currently supports only one type of semiconductor inside device. A mixture of two different semiconductor such as Germanium and Silicon is not allowed.</li>
            <li><strong>Contact naming Restriction:</strongs> Only pre-defined contact names such as DRAIN, GATE, SOURCE, SUB, GATE1 and GATE2 is supported. User defined contact names are not supported in this version.</li>
            <li><strong>Limited Physical models:</strong> Currently doping dependent Caughey-Thomas mobility, Canali model for Field dependent mobility and Lombardi model for mobility degradation at interface is available. Also SRH recombination model is available. Other models will be gradually incorporated in future releases.</li>
            <li><strong>Uniform Rectangular Mesh:</strong> CUrrent Version uses a rectangular mesh uniform through whole region.</li>
           <li><strong>AC Simulation Not supported:</strong>The current Version does not support small signal AC analysis. Only Quasi static DC analysis is possible.</li>
          </ul>
        </div>
      </div>
