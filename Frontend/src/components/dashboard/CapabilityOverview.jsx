import "./CapabilityOverview.css";

export default function CapabilityOverview({ onDetect, onHistory, onDevelopers }) {
  const modules = [
    ["01", "Detección multimodal", "Workspaces independientes para imagen, audio y video; cada filtro ejecuta únicamente el eje seleccionado.", onDetect, "Iniciar análisis"],
    ["02", "Auditoría y trazabilidad", "Casos persistidos en PostgreSQL con modelo, score, SHA-256, metadatos y reporte PDF regenerado en memoria.", onHistory, "Explorar casos"],
    ["03", "API para integraciones", "Conecta tus aplicaciones con endpoints REST para analizar imagen, audio y video, consultar resultados y generar reportes auditables.", onDevelopers, "Explorar API"],
  ];

  return (
    <section className="capability-overview">
      <div className="section-heading centered">
        <span className="section-eyebrow">CICLO DE VERIFICACIÓN</span>
        <h2>Del archivo sospechoso a una evidencia auditable</h2>
        <p>La interfaz separa operación, investigación y exportación para que cada dato conserve su contexto técnico.</p>
      </div>
      <div className="capability-grid">
        {modules.map(([number, title, copy, action, label]) => (
          <article key={number}>
            <span>{number}</span>
            <h3>{title}</h3>
            <p>{copy}</p>
            <button type="button" onClick={action}>{label}</button>
          </article>
        ))}
      </div>
    </section>
  );
}
