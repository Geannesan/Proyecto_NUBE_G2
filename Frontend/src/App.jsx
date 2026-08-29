import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import "./App.css";
import "./styles/theme-dark-lab.css";
import "./styles/detector-section.css";
import "./styles/dashboard-section.css";
import "./styles/platform-sections.css";
import CapabilityOverview from "./components/dashboard/CapabilityOverview";
import DeveloperPortal from "./components/developers/DeveloperPortal";
import DetectorHeader from "./components/detector/DetectorHeader";

const API_URL =
  import.meta.env.VITE_API_URL ?? "";

/*
  Rutas usadas por cada botón.

  La opción Imagen + AI Image Detector conserva tu ruta actual:
  POST http://localhost:8000/analyze

  Puedes cambiar cualquiera de las otras rutas aquí o mediante
  variables VITE_* en tu archivo .env.
*/
const ENDPOINTS = {
  image: {
    ai: "/api/v1/image/analyze",
    deepfake: "/api/v1/image/analyze",
  },
  audio: {
    ai: "/api/v1/audio/analyze",
    deepfake: "/api/v1/audio/analyze",
  },
  video: {
    ai: "/api/v1/video/analyze",
    deepfake: "/api/v1/video/analyze",
  },
};

const MEDIA_CONFIG = {
  audio: {
    label: "AUDIO",
    accept: "audio/*",
    uploadTitle: "Suelta tu audio aquí",
    uploadText:
      "o haz clic para seleccionar un archivo de audio y verificarlo al instante",
    loadingTitle: "Analizando audio...",
    loadingText:
      "El modelo inspecciona la voz, frecuencias, artefactos y patrones de síntesis.",
    previewLabel: "Audio seleccionado",
  },
  image: {
    label: "IMAGEN",
    accept: "image/*",
    uploadTitle: "Suelta tu imagen aquí",
    uploadText:
      "o haz clic para seleccionar una imagen y verificarla al instante",
    loadingTitle: "Analizando imagen...",
    loadingText:
      "El modelo inspecciona patrones visuales, texturas, compresión y posibles evidencias de manipulación.",
    previewLabel: "Imagen seleccionada",
  },
  video: {
    label: "VIDEO",
    accept: "video/*",
    uploadTitle: "Suelta tu video aquí",
    uploadText:
      "o haz clic para seleccionar un video y verificarlo al instante",
    loadingTitle: "Analizando video...",
    loadingText:
      "El modelo inspecciona fotogramas, sincronización, rostros, movimiento y posibles alteraciones.",
    previewLabel: "Video seleccionado",
  },
};

const DETECTOR_CONFIG = {
  audio: {
    ai: "AI Audio Detector",
    deepfake: "Voice Deepfake Detector",
  },
  image: {
    ai: "AI Image Detector",
    deepfake: "Deepfake Detector",
  },
  video: {
    ai: "AI Video Detector",
    deepfake: "Video Deepfake Detector",
  },
};

function ShieldIcon() {
  return (
    <svg
      viewBox="0 0 48 48"
      aria-hidden="true"
      className="brand-icon"
    >
      <path
        d="M24 4 40 10v12c0 10.4-6.4 17.7-16 22C14.4 39.7 8 32.4 8 22V10L24 4Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
      />
      <rect
        x="17"
        y="21"
        width="14"
        height="11"
        rx="2.5"
        fill="currentColor"
      />
      <path
        d="M20 21v-3.2a4 4 0 0 1 8 0V21"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
      />
      <circle cx="24" cy="26.5" r="1.4" fill="#111d38" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path
        d="M32 43V13m0 0L20.5 24.5M32 13l11.5 11.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M13 40v9a4 4 0 0 0 4 4h30a4 4 0 0 0 4-4v-9"
        fill="none"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path
        d="M8 15h8l3-5h10l3 5h8a4 4 0 0 1 4 4v17a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4V19a4 4 0 0 1 4-4Z"
        fill="currentColor"
      />
      <circle cx="24" cy="27" r="8" fill="#a9aaab" />
      <circle cx="24" cy="27" r="5" fill="currentColor" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <circle
        cx="24"
        cy="17"
        r="8"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        d="M8 41c1.5-9.2 7-14 16-14s14.5 4.8 16 14"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <circle
        cx="24"
        cy="24"
        r="20"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
      />
    </svg>
  );
}

function CircuitGraphic({ className = "" }) {
  return (
    <svg
      className={`circuit-graphic ${className}`}
      viewBox="0 0 520 280"
      aria-hidden="true"
    >
      <g fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M0 38h122l28-28h90" />
        <path d="M0 67h180l29-29h116" />
        <path d="M0 96h220l30-30h180" />
        <path d="M0 126h145l30 30h172" />
        <path d="M0 160h240l28-28h177" />
        <path d="M0 195h155l34 34h170" />
        <path d="M0 230h245l26-26h153" />
        <path d="M328 0v42l31 31h109" />
        <path d="M382 0v24l42 42h96" />
        <path d="M438 0v51l26 26h56" />
      </g>

      <g fill="currentColor">
        <circle cx="122" cy="38" r="5" />
        <circle cx="180" cy="67" r="5" />
        <circle cx="220" cy="96" r="5" />
        <circle cx="145" cy="126" r="5" />
        <circle cx="240" cy="160" r="5" />
        <circle cx="155" cy="195" r="5" />
        <circle cx="245" cy="230" r="5" />
        <circle cx="359" cy="73" r="5" />
        <circle cx="424" cy="66" r="5" />
        <circle cx="464" cy="77" r="5" />
      </g>
    </svg>
  );
}

function NetworkGraphic({ className = "" }) {
  const nodes = [
    ["36", "45"],
    ["93", "65"],
    ["148", "47"],
    ["202", "86"],
    ["70", "112"],
    ["121", "111"],
    ["170", "125"],
    ["45", "168"],
    ["106", "183"],
    ["167", "205"],
    ["215", "169"],
  ];

  return (
    <svg
      className={`network-graphic ${className}`}
      viewBox="0 0 260 250"
      aria-hidden="true"
    >
      <g stroke="currentColor" strokeWidth="1.5" opacity="0.8">
        <line x1="36" y1="45" x2="93" y2="65" />
        <line x1="36" y1="45" x2="70" y2="112" />
        <line x1="93" y1="65" x2="148" y2="47" />
        <line x1="93" y1="65" x2="121" y2="111" />
        <line x1="148" y1="47" x2="202" y2="86" />
        <line x1="148" y1="47" x2="170" y2="125" />
        <line x1="70" y1="112" x2="121" y2="111" />
        <line x1="70" y1="112" x2="45" y2="168" />
        <line x1="121" y1="111" x2="170" y2="125" />
        <line x1="121" y1="111" x2="106" y2="183" />
        <line x1="170" y1="125" x2="202" y2="86" />
        <line x1="170" y1="125" x2="215" y2="169" />
        <line x1="45" y1="168" x2="106" y2="183" />
        <line x1="106" y1="183" x2="167" y2="205" />
        <line x1="167" y1="205" x2="215" y2="169" />
        <line x1="106" y1="183" x2="170" y2="125" />
        <line x1="93" y1="65" x2="70" y2="112" />
        <line x1="121" y1="111" x2="148" y2="47" />
      </g>

      <g fill="currentColor">
        {nodes.map(([cx, cy]) => (
          <circle
            key={`${cx}-${cy}`}
            cx={cx}
            cy={cy}
            r="8"
          />
        ))}
      </g>
    </svg>
  );
}

const MEDIA_TECHNOLOGIES = {
  image: {
    ai: [
      ["Vision Transformer", "Distingue patrones globales de generación", "Se refleja en la probabilidad AI frente a HUMAN."],
      ["Análisis de resolución", "Comprueba que la entrada sea técnicamente evaluable", "Se refleja en las dimensiones y cobertura del archivo."],
    ],
    deepfake: [
      ["Detección facial OpenCV", "Localiza rostros antes de buscar manipulaciones", "Se refleja en el número de rostros evaluados."],
      ["Clasificador Celeb-DF", "Busca patrones compatibles con alteración facial", "Se refleja en la probabilidad DEEPFAKE frente a REAL."],
    ],
  },
  audio: {
    ai: [
      ["Wav2Vec2 para voz sintética", "Modela características de audio humano y generado", "Se refleja en la probabilidad AI frente a HUMAN."],
      ["Segmentación solapada", "Evita que un único tramo domine la decisión", "Se refleja en la cantidad y el acuerdo de segmentos."],
      ["Control de calidad acústica", "Detecta silencio, saturación o evidencia insuficiente", "Se refleja en los avisos y casos no concluyentes."],
    ],
    deepfake: [
      ["Wav2Vec2 anti-spoofing", "Busca huellas de clonación o manipulación de voz", "Se refleja en la probabilidad DEEPFAKE frente a REAL."],
      ["Segmentación solapada", "Contrasta distintos tramos de la voz", "Se refleja en la cantidad y el acuerdo de segmentos."],
      ["Control de calidad acústica", "Evita afirmar suplantación con audio insuficiente", "Se refleja en los avisos y casos no concluyentes."],
    ],
  },
  video: {
    ai: [
      ["Ensemble de dos Vision Transformers", "Contrasta dos checkpoints independientes para detectar video generado", "Se refleja en la probabilidad AI/HUMAN, las medianas por modelo y su desacuerdo."],
      ["Muestreo temporal", "Distribuye fotogramas a lo largo de la secuencia", "Se refleja en fotogramas muestreados, válidos y descartados."],
      ["Agregación temporal", "Combina mediana y acuerdo para reducir falsos positivos aislados", "Se refleja en las evidencias y la decisión final."],
    ],
    deepfake: [
      ["Detector facial + Celeb-DF", "Localiza y evalúa rostros manipulados", "Se refleja en la probabilidad DEEPFAKE frente a REAL."],
      ["Muestreo temporal", "Busca persistencia de la manipulación en varios momentos", "Se refleja en fotogramas muestreados, válidos y descartados."],
      ["Agregación temporal", "Exige acuerdo entre cuadros para sostener el hallazgo", "Se refleja en las evidencias y la decisión final."],
    ],
  },
};

const TRACE_TECHNOLOGIES = {
  image: [
    ["EXIF y metadatos técnicos", "Revisa formato, dimensiones, software y datos de captura declarados", "Se refleja en la cobertura y en los metadatos del informe."],
    ["C2PA + SHA-256", "Comprueba Content Credentials y fija la identidad exacta del archivo", "Se refleja en Integridad y trazabilidad; su ausencia no demuestra fraude."],
  ],
  audio: [
    ["FFprobe + SHA-256", "Registra códec, duración, pistas e identidad exacta del archivo", "Se refleja en los metadatos y la trazabilidad del informe."],
    ["Content Credentials C2PA", "Busca procedencia verificable cuando el formato la proporciona", "Se refleja en Integridad; su ausencia no demuestra fraude."],
  ],
  video: [
    ["FFprobe + SHA-256", "Registra códec, FPS, duración, pistas e identidad exacta del archivo", "Se refleja en los metadatos y la trazabilidad del informe."],
    ["Content Credentials C2PA", "Busca procedencia verificable cuando el archivo la proporciona", "Se refleja en Integridad; su ausencia no demuestra fraude."],
  ],
};

function ScoreBar({ label, value, tone }) {
  const safeValue = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div className={`analysis-score ${tone}`}>
      <div><span>{label}</span><strong>{safeValue.toFixed(1)}%</strong></div>
      <div className="analysis-score-track"><i style={{ width: `${safeValue}%` }} /></div>
    </div>
  );
}

function AnalysisInsightDashboard({ result, mediaType, detectorType, narrative }) {
  const metadata = result?.metadata || {};
  const isAi = detectorType === "ai";
  const suspiciousLabel = isAi ? "AI" : (result?.probabilities?.DEEPFAKE !== undefined ? "DEEPFAKE" : "FAKE");
  const normalizedPrediction = String(result?.prediction ?? "").toUpperCase();
  const status = normalizedPrediction === "INCONCLUSIVE"
    ? "inconclusive"
    : ["AI", "DEEPFAKE", "FAKE"].includes(normalizedPrediction) ? "detected" : "not_detected";
  const suspiciousScore = Number(result?.probabilities?.[suspiciousLabel] ?? 0);
  const sampled = Number(metadata.sampled_frames ?? metadata.chunk_count ?? 0);
  const valid = Number(metadata.valid_frames ?? sampled);
  const quality = Number(metadata.quality?.score ?? (sampled > 0 ? (valid / sampled) * 100 : (status === "inconclusive" ? 0 : 100)));
  const technical = metadata.technical_metadata || {};
  const credentialsStatus = metadata.integrity?.content_credentials?.status ?? "unknown";

  const samplingSummary = mediaType === "video"
    ? `${metadata.sampled_frames ?? 0} fotogramas muestreados · ${metadata.valid_frames ?? 0} evaluables`
    : mediaType === "audio"
      ? `${metadata.chunk_count ?? 0} segmentos acústicos analizados`
      : `${metadata.image_width ?? technical.width ?? "?"} × ${metadata.image_height ?? technical.height ?? "?"} píxeles${!isAi ? ` · ${metadata.faces_detected ?? 0} candidatos faciales detectados` : ""}`;

  return (
    <section className="analysis-insight-dashboard">
      <div className="analysis-dashboard-heading">
        <div><span className="section-eyebrow">LECTURA DEL ARCHIVO ACTUAL</span><h3>Qué sostiene este resultado</h3></div>
        <span className="current-file-badge">{mediaType.toUpperCase()}</span>
      </div>
      <div className="analysis-kpi-grid">
        <div><span>{isAi ? "Generación AI" : "Manipulación deepfake"}</span><strong>{suspiciousScore.toFixed(1)}%</strong><small>{status}</small></div>
        <div><span>Clasificación</span><strong>{result?.prediction ?? "N/D"}</strong><small>{isAi ? "AI frente a HUMAN" : "DEEPFAKE frente a REAL"}</small></div>
        <div><span>Calidad de evidencia</span><strong>{quality.toFixed(0)}%</strong><small>{quality >= 70 ? "evidencia utilizable" : "evidencia limitada"}</small></div>
      </div>
      <div className="analysis-graph-grid">
        <div className="analysis-bars-card">
          <h4>Distribución de señales</h4>
          <ScoreBar label={isAi ? "Probabilidad de generación AI" : "Probabilidad de deepfake"} value={suspiciousScore} tone={isAi ? "danger" : "violet"} />
          <ScoreBar label={isAi ? "Probabilidad de origen humano" : "Probabilidad de contenido real"} value={result?.probabilities?.[isAi ? "HUMAN" : "REAL"] ?? 0} tone="success" />
          <ScoreBar label="Calidad técnica" value={quality} tone="success" />
        </div>
        <div className="analysis-context-card">
          <span className="chart-kicker">COBERTURA DEL ANÁLISIS</span>
          <strong>{samplingSummary}</strong>
          <p>{metadata.quality?.notes?.join(" ") || "La entrada fue procesada por los detectores configurados."}</p>
        </div>
      </div>
      <div className="analysis-verdict-copy">
        <span className="chart-kicker">INTERPRETACIÓN</span>
        <h4>Por qué el sistema llegó a esta conclusión</h4>
        <p>{result?.analysis?.model_reason}</p>
        <p>{narrative}</p>
      </div>
      <div className="axis-result-grid">
          <article className={`axis-result-card ${status}`}>
            <div className="axis-card-heading">
              <div><span>{isAi ? "AI frente a HUMAN" : "DEEPFAKE frente a REAL"}</span><h4>{isAi ? "Generación AI" : "Manipulación deepfake"}</h4></div>
              <strong>{suspiciousScore.toFixed(1)}%</strong>
            </div>
            <p><b>Estado:</b> {status} · <b>Resultado:</b> {result?.prediction ?? "no evaluado"}</p>
            {(result?.analysis?.evidence || []).slice(0, 3).map((item, index) => (
              <div className="compact-evidence" key={`${detectorType}-${index}`}><i>✓</i><span>{item}</span></div>
            ))}
          </article>
      </div>
      {!isAi && <div className="identity-notice">
        <span>IDENTIDAD Y SUPLANTACIÓN</span>
        <div><strong>not_assessed</strong><p>Este filtro detecta manipulación facial o vocal. Confirmar la suplantación de una persona concreta requiere una referencia biométrica autorizada.</p></div>
      </div>}
      <div className="analysis-trace-grid">
        <div><span>Modelo ejecutado</span><strong>{result?.model?.name ?? "No disponible"}</strong></div>
        <div><span>Detector aplicado</span><strong>{isAi ? "Generación AI" : "Deepfake"}</strong></div>
        {metadata.integrity?.sha256 && <div><span>SHA-256</span><strong title={metadata.integrity.sha256}>{metadata.integrity.sha256.slice(0, 20)}…</strong></div>}
        {metadata.integrity?.content_credentials && <div><span>Content Credentials</span><strong>{credentialsStatus}</strong></div>}
      </div>
    </section>
  );
}

function AnalysisTechnologies({ result, mediaType, detectorType }) {
  const detectorTechnologies = MEDIA_TECHNOLOGIES[mediaType]?.[detectorType] || [];
  const traceTechnologies = result?.metadata?.integrity
    ? TRACE_TECHNOLOGIES[mediaType] || []
    : [];
  const technologies = [...detectorTechnologies, ...traceTechnologies];
  const executedTechnologies = result?.metadata?.technology_evidence || [];
  const modelNames = [result?.model?.name].filter(Boolean);
  return (
    <section className={`result-technologies ${mediaType}`}>
      <div className="section-heading centered">
        <span className="section-eyebrow">TECNOLOGÍAS ACTIVADAS EN ESTE ANÁLISIS</span>
        <h2>Qué se utilizó, por qué y dónde verlo</h2>
        <p>Estas capacidades corresponden al archivo recién procesado. Cada afirmación apunta a un dato visible en el resultado o en el PDF.</p>
      </div>
      <div className="technology-evidence-grid">
        {(executedTechnologies.length > 0
          ? executedTechnologies.map((item) => [
              item.technology,
              item.purpose,
              item.observation,
              item.status,
            ])
          : technologies.map((item) => [...item, "registrado"])
        ).map(([name, why, reflection, status]) => (
          <article key={name} className={`technology-status-${status}`}>
            <span>{status === "executed" ? "✓ EJECUTADA" : status.toUpperCase()}</span>
            <h3>{name}</h3><p><b>Por qué:</b> {why}</p><p><b>Dato comprobado:</b> {reflection}</p>
          </article>
        ))}
      </div>
      {mediaType === "image" && executedTechnologies.length > 0 && (
        <div className="evidence-matrix">
          <div className="evidence-matrix-head"><span>Tecnología</span><span>Estado</span><span>Evidencia registrada</span></div>
          {executedTechnologies.map((item) => (
            <div className="evidence-matrix-row" key={`matrix-${item.technology}`}>
              <strong>{item.technology}</strong><span className={`matrix-status ${item.status}`}>{item.status}</span><p>{item.observation}</p>
            </div>
          ))}
        </div>
      )}
      {modelNames.length > 0 && <p className="models-used"><b>Checkpoints ejecutados:</b> {modelNames.join(" · ")}</p>}
    </section>
  );
}

function ForensicMetadataPanel({ result, mediaType }) {
  const forensic = result?.metadata?.technical_metadata?.forensic_metadata;
  if (mediaType !== "image" || !forensic) return null;
  const stats = forensic.statistics || {};
  const consistency = forensic.consistency || {};
  const binary = forensic.binary || {};
  const metrics = [
    ["Campos EXIF", stats.exif_fields || 0, Math.min((stats.exif_fields || 0) * 10, 100)],
    ["Campos IPTC", stats.iptc_fields || 0, Math.min((stats.iptc_fields || 0) * 10, 100)],
    ["Tablas DQT", stats.dqt_tables || 0, Math.min((stats.dqt_tables || 0) * 50, 100)],
    ["Marcadores APP", stats.app_segments || 0, Math.min((stats.app_segments || 0) * 20, 100)],
  ];
  return (
    <section className="forensic-metadata-panel">
      <div className="section-heading centered">
        <span className="section-eyebrow">METADATOS FORENSES DEL ARCHIVO ACTUAL</span>
        <h2>Evidencia descriptiva, binaria y de consistencia</h2>
        <p>Los valores se extrajeron del archivo recibido. Refuerzan la trazabilidad, pero ningún metadato aislado determina si una imagen es real o generada.</p>
      </div>
      <div className="forensic-kpis">
        <article><strong>{stats.metadata_coverage_percent || 0}%</strong><span>Cobertura de rastros</span></article>
        <article><strong>{stats.checks_with_observation || 0}/{stats.checks_executed || 0}</strong><span>Pruebas con observación</span></article>
        <article><strong>{consistency.nearest_standard_ratio || "N/D"}</strong><span>Ratio más cercano</span></article>
        <article><strong>{consistency.temporal_status || "N/D"}</strong><span>Coherencia temporal</span></article>
      </div>
      <div className="forensic-grid">
        <article className="forensic-chart"><h3>Disponibilidad de rastros</h3>{metrics.map(([label, count, percent]) => <ScoreBar key={label} label={`${label} (${count})`} value={percent} tone="violet" />)}</article>
        <article className="binary-summary"><h3>Estructura JPEG</h3><p><b>APP:</b> {JSON.stringify(binary.app_markers || {})}</p><p><b>APP1 duplicado:</b> {String(binary.duplicate_app1 || false)}</p><p><b>APP2 duplicado:</b> {String(binary.duplicate_app2 || false)}</p><p><b>Comentarios COM:</b> {(binary.comments || []).join(" · ") || "No presentes"}</p></article>
      </div>
      <div className="forensic-findings">
        <div className="forensic-findings-head"><span>Capa / prueba</span><span>Estado</span><span>Dato e interpretación</span></div>
        {(forensic.findings || []).map((item) => <div className="forensic-finding" key={`${item.category}-${item.check}`}><strong>{item.category}<small>{item.check}</small></strong><span className={`matrix-status ${item.status}`}>{item.status}</span><p>{item.observation} {item.interpretation}</p></div>)}
      </div>
    </section>
  );
}

const SUSPICIOUS_RESULTS = new Set(["AI", "FAKE", "DEEPFAKE", "AI_AND_DEEPFAKE", "SYNTHETIC", "MANIPULATED"]);
const AUTHENTIC_RESULTS = new Set(["HUMAN", "REAL", "REAL_HUMAN", "AUTHENTIC", "BONAFIDE"]);

function PlatformDashboard({ refreshKey, onOpenHistory, onOpenCase }) {
  const [dashboard, setDashboard] = useState(null);
  const [history, setHistory] = useState([]);
  const [dashboardError, setDashboardError] = useState("");
  const [updatedAt, setUpdatedAt] = useState(null);

  useEffect(() => {
    let mounted = true;
    const synchronize = () => Promise.all([
        axios.get(`${API_URL}/api/v1/dashboard/summary`),
        axios.get(`${API_URL}/api/v1/history`, { params: { limit: 40 } }),
      ])
        .then(([summaryResponse, historyResponse]) => {
          if (!mounted) return;
          setDashboard(summaryResponse.data);
          setHistory(historyResponse.data?.items || []);
          setUpdatedAt(new Date());
          setDashboardError("");
        })
        .catch((error) => {
          if (!mounted) return;
          setDashboardError(error.response?.data?.detail || "No fue posible sincronizar las métricas con PostgreSQL.");
        });
    synchronize();
    const intervalId = window.setInterval(synchronize, 15000);
    return () => { mounted = false; window.clearInterval(intervalId); };
  }, [refreshKey]);

  if (!dashboard && !dashboardError) return null;
  if (dashboardError) return <section className="analytics-dashboard"><p className="empty-copy">{dashboardError}</p></section>;

  const total = Number(dashboard.total_analyses || 0);
  const suspicious = Number(dashboard.synthetic_detected || 0);
  const authentic = Number(dashboard.authentic_detected || 0);
  const inconclusive = Number(dashboard.inconclusive || 0);
  const percent = (value) => total ? Math.round((Number(value || 0) / total) * 100) : 0;
  const mediaRows = [
    ["Imágenes", dashboard.total_images],
    ["Audio", dashboard.total_audio],
    ["Video", dashboard.total_videos],
  ];
  const detectorCounts = history.reduce((counts, item) => ({ ...counts, [item.detector_type]: (counts[item.detector_type] || 0) + 1 }), {});
  const confidenceBands = history.reduce((bands, item) => {
    const score = Number(item.confidence || 0);
    const key = score >= 80 ? "Alta (80–100)" : score >= 60 ? "Media (60–79)" : "Baja (<60)";
    return { ...bands, [key]: (bands[key] || 0) + 1 };
  }, {});
  const activity = Array.from({ length: 7 }, (_, offset) => {
    const date = new Date(); date.setDate(date.getDate() - (6 - offset));
    const key = date.toISOString().slice(0, 10);
    return { label: date.toLocaleDateString(undefined, { weekday: "short" }).slice(0, 3), count: history.filter((item) => String(item.created_at || "").slice(0, 10) === key).length };
  });
  const activityMax = Math.max(1, ...activity.map((item) => item.count));

  return (
    <section className="analytics-dashboard" id="dashboard-operativo">
      <div className="section-heading">
        <div><span className="section-eyebrow">DASHBOARD SINCRONIZADO</span><h2>Métricas de análisis almacenadas</h2><p>Estas cifras se consultan desde PostgreSQL y se actualizan después de cada análisis. Describen operación y resultados; no sustituyen métricas de accuracy sobre ground truth.</p></div>
        <span className="live-badge"><i /> EN VIVO · {updatedAt ? updatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "SINCRONIZANDO"}</span>
      </div>
      <div className="metric-grid">
        <article className="metric-card"><span className="metric-label">Análisis almacenados</span><strong>{total}</strong><p>Registros persistidos por la API.</p></article>
        <article className="metric-card danger"><span className="metric-label">Hallazgos sospechosos</span><strong>{suspicious}</strong><p>{percent(suspicious)}% del volumen procesado.</p></article>
        <article className="metric-card success"><span className="metric-label">Real / humano</span><strong>{authentic}</strong><p>{percent(authentic)}% del volumen procesado.</p></article>
        <article className="metric-card warning"><span className="metric-label">No concluyentes</span><strong>{inconclusive}</strong><p>{percent(inconclusive)}% requiere mejor evidencia.</p></article>
        <article className="metric-card"><span className="metric-label">Score medio</span><strong>{Number(dashboard.average_model_confidence || 0).toFixed(1)}%</strong><p>Promedio operativo; no equivale a accuracy validada.</p></article>
      </div>
      <div className="charts-grid">
        <article className="chart-card">
          <div className="chart-title-row"><div><span className="chart-kicker">COBERTURA</span><h3>Análisis por formato</h3></div><strong>{total}</strong></div>
          <div className="bar-list">{mediaRows.map(([label, value]) => <div className="bar-row" key={label}><div><span>{label}</span><b>{value || 0}</b></div><div className="dashboard-bar"><i style={{ width: `${percent(value)}%` }} /></div></div>)}</div>
        </article>
        <article className="chart-card donut-card"><div className="dashboard-donut red" style={{ "--chart-value": `${percent(suspicious)}%` }}><span>{percent(suspicious)}%</span></div><h3>Tasa de hallazgos</h3><p>Proporción marcada como IA o deepfake; no es tasa de acierto.</p></article>
        <article className="chart-card donut-card"><div className="dashboard-donut amber" style={{ "--chart-value": `${percent(inconclusive)}%` }}><span>{percent(inconclusive)}%</span></div><h3>Abstención</h3><p>Casos donde el sistema evitó una afirmación firme.</p></article>
      </div>
      <div className="dashboard-detail-grid">
        <article className="chart-card activity-card"><div className="chart-title-row"><div><span className="chart-kicker">RITMO OPERATIVO</span><h3>Actividad de los últimos 7 días</h3></div><span className="pulse-dot" /></div><div className="activity-columns">{activity.map((item) => <div key={item.label}><div className="activity-track"><i style={{ height: `${Math.max(item.count ? 12 : 3, (item.count / activityMax) * 100)}%` }}><b>{item.count || ""}</b></i></div><span>{item.label}</span></div>)}</div></article>
        <article className="chart-card"><div className="chart-title-row"><div><span className="chart-kicker">EJES SOLICITADOS</span><h3>Uso por detector</h3></div></div><div className="detector-split"><div style={{ "--split": `${history.length ? Math.round(((detectorCounts.ai || 0) / history.length) * 100) : 0}%` }} /><section><span><i className="ai-dot" />Generación AI <b>{detectorCounts.ai || 0}</b></span><span><i className="deepfake-dot" />Deepfake <b>{detectorCounts.deepfake || 0}</b></span></section></div></article>
        <article className="chart-card"><div className="chart-title-row"><div><span className="chart-kicker">DISTRIBUCIÓN</span><h3>Bandas de score</h3></div></div><div className="confidence-band-list">{["Alta (80–100)", "Media (60–79)", "Baja (<60)"].map((label) => <div key={label}><span>{label}</span><strong>{confidenceBands[label] || 0}</strong><i><b style={{ width: `${history.length ? ((confidenceBands[label] || 0) / history.length) * 100 : 0}%` }} /></i></div>)}</div></article>
      </div>
      <div className={`validation-banner ${dashboard.validation?.ground_truth_available ? "validated" : ""}`}><span className="validation-icon">!</span><div><strong>{dashboard.validation?.ground_truth_available ? "Validación externa cargada" : "Validación científica pendiente"}</strong><p>{dashboard.validation?.message}</p></div></div>
      <div className="history-panel">
        <div className="panel-heading"><div><span className="chart-kicker">TRAZABILIDAD</span><h3>Últimos análisis almacenados</h3></div><button className="text-action" type="button" onClick={onOpenHistory}>Ver historial completo →</button></div>
        <div className="history-list">{history.slice(0, 8).map((item) => {
          const prediction = String(item.prediction || "").toUpperCase();
          const statusClass = prediction === "INCONCLUSIVE" ? "warning" : AUTHENTIC_RESULTS.has(prediction) ? "success" : SUSPICIOUS_RESULTS.has(prediction) ? "" : "warning";
          return <div className="history-row" key={item.analysis_id}><span className={`history-status ${statusClass}`}>{item.prediction}</span><div className="history-file"><strong>{item.filename}</strong><span>{item.media_type} · {item.detector_type} · {new Date(item.created_at).toLocaleString()}</span></div><div className="history-confidence"><strong>{Number(item.confidence || 0).toFixed(1)}%</strong><span>score del modelo</span></div><button className="row-case-link" type="button" onClick={() => onOpenCase(item.analysis_id)}>Abrir caso</button><a href={`${API_URL}/api/v1/reports/${item.analysis_id}`} target="_blank" rel="noreferrer">PDF ↗</a></div>;
        })}</div>
      </div>
    </section>
  );
}

function FullHistory({ onOpenCase }) {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const [mediaFilter, setMediaFilter] = useState("all");
  const [verdictFilter, setVerdictFilter] = useState("all");
  useEffect(() => { axios.get(`${API_URL}/api/v1/history`, { params: { limit: 200 } }).then((response) => setItems(response.data?.items || [])); }, []);
  const visible = items.filter((item) => {
    const search = query.trim().toLowerCase();
    const hash = item.metadata?.integrity?.sha256 || "";
    return (!search || `${item.filename} ${hash}`.toLowerCase().includes(search)) && (mediaFilter === "all" || item.media_type === mediaFilter) && (verdictFilter === "all" || String(item.prediction).toUpperCase() === verdictFilter);
  });
  const downloadData = (format) => {
    const content = format === "json" ? JSON.stringify(visible, null, 2) : ["id,fecha,archivo,medio,detector,resultado,score,sha256", ...visible.map((item) => [item.analysis_id, item.created_at, item.filename, item.media_type, item.detector_type, item.prediction, item.confidence, item.metadata?.integrity?.sha256 || ""].map((value) => `"${String(value ?? "").replaceAll('"', '""')}"`).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob([content], { type: format === "json" ? "application/json" : "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `deepfakeshield-historial.${format}`; link.click(); URL.revokeObjectURL(url);
  };
  return <section className="history-workspace"><div className="workspace-heading"><div><span className="section-eyebrow">LOG DE TRAZABILIDAD</span><h2>Historial completo de análisis</h2><p>Consulta por archivo o SHA-256 y abre la evidencia persistida de cada caso.</p></div><strong>{visible.length} resultados</strong></div><div className="history-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar nombre o hash SHA-256…"/><select value={mediaFilter} onChange={(event) => setMediaFilter(event.target.value)}><option value="all">Todos los formatos</option><option value="image">Imagen</option><option value="audio">Audio</option><option value="video">Video</option></select><select value={verdictFilter} onChange={(event) => setVerdictFilter(event.target.value)}><option value="all">Todos los veredictos</option><option value="AI">AI</option><option value="HUMAN">HUMAN</option><option value="FAKE">FAKE</option><option value="REAL">REAL</option><option value="INCONCLUSIVE">INCONCLUSIVE</option></select><button onClick={() => downloadData("csv")}>CSV ↓</button><button onClick={() => downloadData("json")}>JSON ↓</button></div><div className="audit-table"><div className="audit-head"><span>Resultado</span><span>Archivo y fecha</span><span>Formato / eje</span><span>Score</span><span>Acciones</span></div>{visible.map((item) => <div className="audit-row" key={item.analysis_id}><b>{item.prediction}</b><div><strong>{item.filename}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div><span>{item.media_type} · {item.detector_type}</span><strong>{Number(item.confidence || 0).toFixed(1)}%</strong><div><button onClick={() => onOpenCase(item.analysis_id)}>Caso</button><a href={`${API_URL}/api/v1/reports/${item.analysis_id}`} target="_blank" rel="noreferrer">PDF</a></div></div>)}</div></section>;
}

function CaseViewer({ analysisId, onBack }) {
  const [record, setRecord] = useState(null);
  useEffect(() => { axios.get(`${API_URL}/api/v1/history/${analysisId}`).then((response) => setRecord(response.data)); }, [analysisId]);
  if (!record) return <section className="case-viewer"><p>Cargando evidencia del caso…</p></section>;
  const metadata = record.metadata || {};
  const technologies = metadata.technology_evidence || [];
  const forensic = metadata.technical_metadata?.forensic_metadata;
  return <section className="case-viewer"><button className="back-action" onClick={onBack}>← Volver al historial</button><div className="case-hero"><div><span className="section-eyebrow">EXPEDIENTE {record.analysis_id}</span><h2>{record.filename}</h2><p>{record.media_type} · {record.detector_type} · {new Date(record.created_at).toLocaleString()}</p></div><div className="case-verdict"><span>{record.prediction}</span><strong>{Number(record.confidence || 0).toFixed(1)}%</strong></div></div><div className="case-actions"><a href={`${API_URL}/api/v1/reports/${record.analysis_id}`} target="_blank" rel="noreferrer">Exportar PDF</a><button onClick={() => navigator.clipboard?.writeText(metadata.integrity?.sha256 || "")}>Copiar SHA-256</button></div><div className="case-facts"><article><span>Modelo</span><strong>{record.model_name || "N/D"}</strong></article><article><span>SHA-256</span><strong>{metadata.integrity?.sha256 || "N/D"}</strong></article><article><span>C2PA</span><strong>{metadata.integrity?.content_credentials?.status || "N/D"}</strong></article></div><h3 className="case-section-title">Matriz de evidencia ejecutada</h3><div className="evidence-matrix"><div className="evidence-matrix-head"><span>Tecnología</span><span>Estado</span><span>Evidencia registrada</span></div>{technologies.map((item) => <div className="evidence-matrix-row" key={item.technology}><strong>{item.technology}</strong><span className={`matrix-status ${item.status}`}>{item.status}</span><p>{item.observation}</p></div>)}</div>{forensic ? <div className="case-data-notice">Este expediente contiene {forensic.statistics?.checks_executed || 0} comprobaciones de metadatos y {forensic.statistics?.dqt_tables || 0} tablas DQT. El detalle completo está disponible en el PDF.</div> : <div className="case-data-notice">Este registro no contiene evidencia visual localizada. No se muestra un heatmap porque el checkpoint ejecutado no produjo un mapa de atención verificable.</div>}</section>;
}

function App() {
  const [view, setView] = useState("home");
  const [selectedCase, setSelectedCase] = useState(null);
  const [activeMedia, setActiveMedia] = useState("image");
  const [activeDetector, setActiveDetector] =
    useState("ai");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [dashboardRefresh, setDashboardRefresh] = useState(0);

  const fileInputRef = useRef(null);

  const media = MEDIA_CONFIG[activeMedia];
  const detectorLabels = DETECTOR_CONFIG[activeMedia];
  const currentEndpoint =
    ENDPOINTS[activeMedia][activeDetector];

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  const confidence = useMemo(() => {
    const rawValue = Number(result?.confidence ?? 0);

    if (!Number.isFinite(rawValue)) {
      return 0;
    }

    const percentage =
      rawValue > 0 && rawValue <= 1
        ? rawValue * 100
        : rawValue;

    return Math.min(100, Math.max(0, percentage));
  }, [result]);

  const clearCurrentFile = () => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(null);
    setPreview("");
    setResult(null);
    setDragging(false);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const selectMedia = (mediaType) => {
    if (mediaType === activeMedia) return;

    clearCurrentFile();
    setActiveMedia(mediaType);
    setActiveDetector("ai");
  };

  const selectDetector = (detectorType) => {
    if (detectorType === activeDetector) return;

    setActiveDetector(detectorType);
    setResult(null);
  };

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;

    const expectedType = `${activeMedia}/`;

    if (!selectedFile.type.startsWith(expectedType)) {
      alert(
        `El archivo seleccionado debe ser de tipo ${media.label.toLowerCase()}.`
      );
      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setResult(null);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    handleFile(event.dataTransfer.files?.[0]);
  };

  const analyzeFile = async () => {
    if (!file) {
      fileInputRef.current?.click();
      return;
    }

    const formData = new FormData();

    formData.append("file", file);
    formData.append("media_type", activeMedia);
    formData.append("detector_type", activeDetector);

    try {
      setLoading(true);
      setResult(null);

      const response = await axios.post(
        `${API_URL}${currentEndpoint}`,
        formData
      );

      setResult(response.data);
      setDashboardRefresh((value) => value + 1);
    } catch (error) {
      console.error("Error completo:", error);
      console.error("Respuesta backend:", error.response?.data);

      const backendDetail =
        error.response?.data?.detail ||
        error.message ||
        "Error desconocido";

      const status =
        error.response?.status ||
        "Sin respuesta";

      alert(
        `No fue posible completar el análisis.\n\n` +
        `Estado: ${status}\n` +
        `Ruta utilizada: ${currentEndpoint}\n` +
        `Detalle: ${backendDetail}`
      );
    } finally {
      setLoading(false);
    }
  };

  const resultClass = () => {
    const prediction = String(
      result?.prediction ??
        result?.label ??
        result?.result ??
        ""
    ).toLowerCase();

    if (
      prediction.includes("inconclusive") ||
      prediction.includes("no concluyente")
    ) {
      return "inconclusive";
    }

    return prediction.includes("fake") ||
      prediction.includes("ai") ||
      prediction.includes("ia") ||
      prediction.includes("falso") ||
      prediction.includes("manipulado")
      ? "fake"
      : "real";
  };

  const rawPredictionText =
    result?.prediction ??
    result?.label ??
    result?.result ??
    "Resultado recibido";

  const predictionText =
    String(rawPredictionText).toUpperCase() ===
    "INCONCLUSIVE"
      ? "NO CONCLUYENTE"
      : rawPredictionText;

  const normalizedPrediction = String(result?.prediction ?? "").toUpperCase();
  const isSuspicious = ["AI", "DEEPFAKE", "FAKE"].includes(normalizedPrediction);
  const focusedNarrative = normalizedPrediction === "INCONCLUSIVE"
    ? "La evidencia de este detector no es suficiente para emitir una conclusión firme. Se recomienda usar el archivo original, con mejor calidad y menor compresión."
    : isSuspicious
      ? `El detector ${activeDetector === "ai" ? "de generación" : "de deepfake"} encontró señales consistentes. La conclusión se apoya en ${result?.analysis?.evidence?.length ?? 0} indicadores del modelo seleccionado.`
      : `El detector ${activeDetector === "ai" ? "de generación" : "de deepfake"} no alcanzó el umbral de evidencia sospechosa. Esto reduce la sospecha para este eje, pero no evalúa automáticamente el otro.`;

  const renderPreview = () => {
    if (!preview) return null;

    if (activeMedia === "image") {
      return (
        <img
          src={preview}
          className="preview preview-image"
          alt={media.previewLabel}
        />
      );
    }

    if (activeMedia === "audio") {
      return (
        <audio
          className="preview preview-audio"
          src={preview}
          controls
          onClick={(event) => event.stopPropagation()}
        >
          Tu navegador no soporta la reproducción de audio.
        </audio>
      );
    }

    return (
      <video
        className="preview preview-video"
        src={preview}
        controls
        onClick={(event) => event.stopPropagation()}
      >
        Tu navegador no soporta la reproducción de video.
      </video>
    );
  };

  const openCase = (analysisId) => { setSelectedCase(analysisId); setView("case"); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const navigate = (nextView) => { setView(nextView); if (nextView !== "case") setSelectedCase(null); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <main className={`page view-${view}`}>
      <div className="polygon polygon--left" />
      <div className="polygon polygon--right" />

      <CircuitGraphic className="circuit-graphic--top" />
      <CircuitGraphic className="circuit-graphic--bottom" />
      <NetworkGraphic className="network-graphic--left" />
      <NetworkGraphic className="network-graphic--right" />

      <div className="content">
        <nav className="platform-nav" aria-label="Navegación principal">
          <button className="nav-brand" type="button" onClick={() => navigate("home")}><ShieldIcon /><span>DeepFakeShield</span></button>
          <div>{[["home", "Dashboard"], ["detect", "Detectar"], ["history", "Historial"], ["developers", "API"]].map(([key, label]) => <button type="button" key={key} className={view === key ? "active" : ""} onClick={() => navigate(key)}>{label}</button>)}</div>
        </nav>
        {view === "home" && <>
          <header className="hero editorial-hero">
            <div className="editorial-wordmark" aria-label="DeepFakeShield" style={{ textAlign: 'center' }}><span>DEEPFAKESHIELD</span></div>
            <div className="hero-editorial-grid">
              <div className="hero-editorial-copy"><h1>Lo real deja<br/><em>evidencia.</em></h1><p>Analiza imagen, voz y video. Separa generación artificial de manipulación deepfake y conserva cada hallazgo como un expediente trazable.</p><div className="hero-actions"><button type="button" onClick={() => navigate("detect")}>Comenzar análisis</button><button type="button" className="secondary" onClick={() => navigate("history")}>Ver investigaciones</button></div></div>
              <figure className="hero-editorial-image"><img src="/images/deepfakeshield-editorial-hero.png" alt="Rostro dividido entre identidad humana y reconstrucción digital"/><figcaption><span>HUMANO</span><span>SINTÉTICO</span></figcaption></figure>
            </div>
          </header>
          <div className="signal-marquee" aria-hidden="true"><div>{[0, 1].map((copy) => <div className="marquee-set" key={copy}><span>IMAGEN</span><i>↗</i><span>AUDIO</span><i>↗</i><span>VIDEO</span><i>↗</i><span>PROCEDENCIA</span><i>↗</i><span>TRAZABILIDAD</span><i>↗</i></div>)}</div></div>
          <section className="editorial-flow"><span className="vertical-label">FLUJO FORENSE</span><div className="flow-track">{[["01", "RECIBE", "Archivo original"], ["02", "INSPECCIONA", "Modelo y metadatos"], ["03", "CONTRASTA", "Ejes independientes"], ["04", "DOCUMENTA", "Hash e informe"]].map(([number, title, copy]) => <article key={number}><b>{number}</b><h3>{title}</h3><p>{copy}</p><i>→</i></article>)}</div></section>
        </>}

        {view === "detect" && <DetectorHeader />}

        {view === "detect" && (
        <section className="detector-shell">
          <nav
            className="media-switch"
            aria-label="Tipo de contenido"
          >
            {Object.keys(MEDIA_CONFIG).map((mediaType) => (
              <button
                key={mediaType}
                type="button"
                className={
                  activeMedia === mediaType ? "active" : ""
                }
                aria-pressed={activeMedia === mediaType}
                onClick={() => selectMedia(mediaType)}
              >
                {MEDIA_CONFIG[mediaType].label}
              </button>
            ))}
          </nav>

          <nav
            className="sub-switch"
            aria-label="Tipo de detector"
          >
            {Object.keys(detectorLabels).map((detectorType) => (
              <button
                key={detectorType}
                type="button"
                className={activeDetector === detectorType ? "active" : ""}
                aria-pressed={activeDetector === detectorType}
                onClick={() => selectDetector(detectorType)}
              >
                {detectorLabels[detectorType]}
              </button>
            ))}
          </nav>

          <section className="metal-panel">
            <span className="screw screw--tl" />
            <span className="screw screw--tr" />
            <span className="screw screw--bl" />
            <span className="screw screw--br" />

            <div
              className="device-controls"
              aria-hidden="true"
            >
              <span className="status-light" />
              <CameraIcon />
              <UserIcon />
            </div>

            <div
              className={`drop-area ${
                dragging ? "dragging" : ""
              } ${file ? "has-file" : ""}`}
              onClick={() =>
                fileInputRef.current?.click()
              }
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (
                  event.key === "Enter" ||
                  event.key === " "
                ) {
                  fileInputRef.current?.click();
                }
              }}
            >
              <input
                ref={fileInputRef}
                key={`${activeMedia}-${activeDetector}`}
                type="file"
                accept={media.accept}
                onChange={(event) =>
                  handleFile(event.target.files?.[0])
                }
              />

              {preview ? (
                <div
                  className="preview-wrap"
                  onClick={(event) =>
                    event.stopPropagation()
                  }
                >
                  {renderPreview()}

                  <span className="file-name">
                    {file?.name}
                  </span>

                  <button
                    type="button"
                    className="change-file-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      fileInputRef.current?.click();
                    }}
                  >
                    Cambiar archivo
                  </button>
                </div>
              ) : (
                <>
                  <div className="upload-icon">
                    <UploadIcon />
                  </div>

                  <h2>{media.uploadTitle}</h2>
                  <p>{media.uploadText}</p>
                </>
              )}

              <button
                type="button"
                className="primary-button"
                onClick={(event) => {
                  event.stopPropagation();
                  analyzeFile();
                }}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="button-spinner" />
                    Analizando...
                  </>
                ) : (
                  "Comprobar Autenticidad"
                )}
              </button>
            </div>
          </section>

          <div className="selected-mode" aria-live="polite">
            <span>{media.label}</span>
            <strong>
              {detectorLabels[activeDetector]}
            </strong>
          </div>

          {loading && (
            <section
              className="processing-card"
              aria-live="polite"
            >
              <div className="scanner-line" />
              <h2>{media.loadingTitle}</h2>
              <p>{media.loadingText}</p>
            </section>
          )}

          {result && (
            <section
              className={`result-card ${resultClass()}`}
              aria-live="polite"
            >
              <div className="result-heading">
                <div>
                  <span className="eyebrow">
                    RESULTADO DEL ANÁLISIS
                  </span>
                  <h2>{predictionText}</h2>
                </div>

                <div
                  className="confidence-ring"
                  style={{
                    "--confidence": `${confidence * 3.6}deg`,
                  }}
                >
                  <span>
                    {confidence.toFixed(0)}%
                  </span>
                </div>
              </div>

              <div className="confidence-block">
                <div className="confidence-label">
                  <span>Nivel de confianza</span>
                  <strong>
                    {confidence.toFixed(1)}%
                  </strong>
                </div>

                <div className="confidence-bar">
                  <div
                    className="confidence-progress"
                    style={{
                      width: `${confidence}%`,
                    }}
                  />
                </div>
              </div>

              <AnalysisInsightDashboard
                result={result}
                mediaType={activeMedia}
                detectorType={activeDetector}
                narrative={focusedNarrative}
              />
              <AnalysisTechnologies result={result} mediaType={activeMedia} detectorType={activeDetector} />
              <ForensicMetadataPanel result={result} mediaType={activeMedia} />

              {result?.analysis_id && (
                <a
                  className="primary-button report-link"
                  href={`${API_URL}/api/v1/reports/${result.analysis_id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Descargar reporte técnico PDF
                </a>
              )}
            </section>
          )}
        </section>
        )}

        {view === "home" && <><PlatformDashboard refreshKey={dashboardRefresh} onOpenHistory={() => navigate("history")} onOpenCase={openCase} /><CapabilityOverview onDetect={() => navigate("detect")} onHistory={() => navigate("history")} /></>}
        {view === "history" && <FullHistory onOpenCase={openCase} />}
        {view === "case" && selectedCase && <CaseViewer analysisId={selectedCase} onBack={() => navigate("history")} />}
        {view === "developers" && <DeveloperPortal apiUrl={API_URL} />}

      </div>

    

      <footer className="footer">
        <div className="footer-links">
          <a href="#deep-links">🇪🇨 Deep Links</a>
          <a href="#contacts">Contactos</a>
          <a href="#privacy">Privacidad</a>
          <a href="#terms">Términos</a>
        </div>
      </footer>
    </main>
  );
}

export default App;
