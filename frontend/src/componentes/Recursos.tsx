import { Recurso } from "../api";

const etiqueta = { INSTITUCIONAL: "Universidad", LINEA_APOYO: "Línea de apoyo", EMERGENCIA: "Emergencia" };

export function TarjetaRecurso({ r }: { r: Recurso }) {
  return (
    <div className={`recurso recurso-${r.tipo.toLowerCase()}`}>
      <div className="recurso-cab">
        <span className="chip">{etiqueta[r.tipo]}</span>
        {r.telefono && <a className="telefono" href={`tel:${r.telefono.split(/[ ·(]/)[0]}`}>{r.telefono}</a>}
      </div>
      <strong>{r.nombre}</strong>
      {r.ubicacion && <p>{r.ubicacion}</p>}
      {r.horario && <p className="tenue">{r.horario}</p>}
      {r.procedimiento && <p className="tenue">{r.procedimiento}</p>}
    </div>
  );
}

export default function PanelRecursos({ recursos }: { recursos: Recurso[] }) {
  return (
    <aside className="panel-recursos">
      <h3>Recursos de apoyo</h3>
      <p className="tenue">Atención psicológica gratuita y confidencial. Puedes acudir cuando quieras, sin necesidad de usar este asistente.</p>
      {recursos.map((r) => <TarjetaRecurso key={r.id} r={r} />)}
    </aside>
  );
}
