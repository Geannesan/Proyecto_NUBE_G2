import "./DeveloperPortal.css";

export default function DeveloperPortal({ apiUrl = "" }) {
  return (
    <section className="developer-portal">
      <div className="workspace-heading">
        <div>
          <span className="section-eyebrow">INTEGRACIÓN</span>
          <h2>API y documentación técnica</h2>
          <p>Integra los mismos analizadores usados por el frontend mediante los endpoints publicados por FastAPI.</p>
        </div>
        <span className="api-live">API ACTIVA</span>
      </div>
      <div className="developer-grid">
        <article><span>OPENAPI</span><h3>Documentación interactiva</h3><p>Consulta esquemas, parámetros y prueba las rutas desde Swagger.</p><a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer">Abrir Swagger ↗</a></article>
        <article><span>FORMATOS</span><h3>Imagen, audio y video</h3><p>Rutas independientes con selector explícito para generación AI o manipulación deepfake.</p></article>
        <article><span>TRAZABILIDAD</span><h3>Respuestas auditables</h3><p>Cada resultado devuelve identificador, checkpoint, evidencia, hash y vínculo de reporte.</p></article>
      </div>
      <div className="integration-note"><strong>API keys, procesamiento batch y webhooks</strong><p>Se muestran como siguiente etapa de integración, no como servicios activos. Requieren autenticación, colas de trabajo, rotación de secretos y control de cuotas antes de exponerse.</p></div>
    </section>
  );
}
