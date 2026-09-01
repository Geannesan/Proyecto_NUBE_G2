import { useEffect, useState } from "react";
import "./DeveloperPortal.css";

export default function DeveloperPortal({ apiUrl = "" }) {
  const [apiStatus, setApiStatus] = useState({ state: "checking", latency: null });

  useEffect(() => {
    let mounted = true;
    const checkApi = async () => {
      const startedAt = performance.now();
      try {
        const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
        if (!response.ok) throw new Error("API unavailable");
        if (mounted) setApiStatus({ state: "online", latency: Math.round(performance.now() - startedAt) });
      } catch {
        if (mounted) setApiStatus({ state: "offline", latency: null });
      }
    };
    checkApi();
    const intervalId = window.setInterval(checkApi, 30000);
    return () => { mounted = false; window.clearInterval(intervalId); };
  }, [apiUrl]);

  const statusCopy = apiStatus.state === "online" ? `API ACTIVA · ${apiStatus.latency} MS` : apiStatus.state === "offline" ? "API SIN CONEXIÓN" : "COMPROBANDO API";

  return (
    <section className="developer-portal">
      <div className="workspace-heading">
        <div>
          <span className="section-eyebrow">INTEGRACIÓN</span>
          <h2>API y documentación técnica</h2>
          <p>Integra los mismos analizadores usados por el frontend mediante los endpoints publicados por FastAPI.</p>
        </div>
        <span className={`api-live ${apiStatus.state}`}><i />{statusCopy}</span>
      </div>
      <div className="developer-grid">
        <article><b className="developer-card-index">01</b><span>OPENAPI</span><h3>Documentación interactiva</h3><p>Consulta esquemas, parámetros y prueba las rutas desde Swagger sin configurar un cliente externo.</p><div className="developer-tags"><em>Swagger UI</em><em>JSON Schema</em></div><a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer">Abrir Swagger <i>↗</i></a></article>
        <article><b className="developer-card-index">02</b><span>FORMATOS</span><h3>Imagen, audio y video</h3><p>Rutas independientes para distinguir generación sintética y manipulación deepfake según el medio.</p><div className="developer-tags"><em>Multipart</em><em>Async ready</em></div></article>
        <article><b className="developer-card-index">03</b><span>TRAZABILIDAD</span><h3>Respuestas auditables</h3><p>Cada resultado incluye identificador, modelo, evidencia, hash SHA-256 y un reporte descargable.</p><div className="developer-tags"><em>SHA-256</em><em>PDF report</em></div></article>
      </div>

      <div className="api-flow" aria-label="Flujo de análisis por API">
        <div className="api-flow-heading"><span>FLUJO DE UNA SOLICITUD</span><p>Del archivo al resultado verificable</p></div>
        <ol>
          <li><i>1</i><div><strong>Enviar evidencia</strong><span>Archivo + tipo de detector</span></div></li>
          <li><i>2</i><div><strong>Validar integridad</strong><span>Formato, tamaño y hash</span></div></li>
          <li><i>3</i><div><strong>Ejecutar modelo</strong><span>Inferencia y señales técnicas</span></div></li>
          <li><i>4</i><div><strong>Recibir expediente</strong><span>Veredicto, score y reporte</span></div></li>
        </ol>
      </div>

      <div className="developer-details-grid">
        <article className="endpoint-catalog">
          <div className="detail-heading"><span>ENDPOINTS PRINCIPALES</span><strong>REST / JSON</strong></div>
          <div><code>POST</code><p><b>/api/v1/image/analyze</b><small>Análisis forense de imágenes</small></p><em>multipart/form-data</em></div>
          <div><code>POST</code><p><b>/api/v1/audio/analyze</b><small>Detección sobre señales de audio</small></p><em>multipart/form-data</em></div>
          <div><code>GET</code><p><b>/api/v1/history</b><small>Consulta de resultados persistidos</small></p><em>application/json</em></div>
        </article>
        <article className="response-preview">
          <div className="detail-heading"><span>ANATOMÍA DEL RESULTADO</span><strong>200 OK</strong></div>
          <pre><span>{`{`}</span>{`\n  "analysis_id": "a8f2…",\n  "prediction": "DEEPFAKE",\n  "confidence": 87.4,\n  "integrity": { "sha256": "…" },\n  "report_url": "/reports/a8f2…"\n`}<span>{`}`}</span></pre>
        </article>
      </div>

      <div className="integration-note"><div><strong>Preparada para crecer</strong><p>La arquitectura ya separa análisis, persistencia y reportes. Las siguientes capacidades requieren seguridad y operación antes de exponerse.</p></div><div className="roadmap-pills"><span>API keys</span><span>Procesamiento batch</span><span>Webhooks</span><span>Cuotas</span></div></div>
    </section>
  );
}
