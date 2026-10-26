import { useEffect, useState } from "react";
import { api, fecha } from "../api";

const PRIORIDAD: Record<string, string> = { CRITICA: "Crítica", ALTA: "Alta", NORMAL: "Normal" };
const NOMBRES_ESTADO: Record<string, string> = {
  NUEVA: "Nueva", EN_REVISION: "En revisión", CONTACTADO: "Contactado", AGENDADA: "Agendada",
  NO_LOCALIZADO: "No localizado", FINALIZADA: "Finalizada", CANCELADA: "Cancelada",
};
const ESTADO = (e: string) => NOMBRES_ESTADO[e] ?? e;

export default function Atencion() {
  const [lista, setLista] = useState<any[]>([]);
  const [filtro, setFiltro] = useState({ prioridad: "", estado: "" });
  const [detalle, setDetalle] = useState<any | null>(null);
  const [nuevoEstado, setNuevoEstado] = useState("");
  const [comentario, setComentario] = useState("");
  const [notificaciones, setNotificaciones] = useState<any[]>([]);
  const [error, setError] = useState("");

  const cargar = () => {
    const q = new URLSearchParams(Object.entries(filtro).filter(([, v]) => v)).toString();
    api<any[]>(`/api/atencion/solicitudes${q ? `?${q}` : ""}`).then(setLista);
    api<any[]>("/api/atencion/notificaciones").then(setNotificaciones);
  };
  useEffect(cargar, [filtro]);

  const abrir = async (id: string) => {
    setError(""); setComentario("");
    const d = await api(`/api/atencion/solicitudes/${id}`);
    setDetalle(d); setNuevoEstado(d.transiciones_permitidas[0] ?? "");
  };

  const cambiar = async () => {
    try {
      await api(`/api/atencion/solicitudes/${detalle.id}/estado`, { cuerpo: { estado: nuevoEstado, comentario: comentario || null } });
      await abrir(detalle.id); cargar();
    } catch (e) { setError((e as Error).message); }
  };

  const sinLeer = notificaciones.filter((n) => !n.leida).length;
  return (
    <div className="atencion">
      <section className="bandeja">
        <div className="fila-entre">
          <h2>Bandeja de solicitudes</h2>
          <span className="campana" title="Notificaciones sin leer">🔔 {sinLeer}</span>
        </div>
        <div className="filtros">
          <select value={filtro.prioridad} onChange={(e) => setFiltro({ ...filtro, prioridad: e.target.value })}>
            <option value="">Todas las prioridades</option>
            <option value="CRITICA">Crítica</option><option value="ALTA">Alta</option><option value="NORMAL">Normal</option>
          </select>
          <select value={filtro.estado} onChange={(e) => setFiltro({ ...filtro, estado: e.target.value })}>
            <option value="">Solicitudes activas</option>
            {["NUEVA", "EN_REVISION", "CONTACTADO", "AGENDADA", "NO_LOCALIZADO", "FINALIZADA"].map((e) => <option key={e} value={e}>{ESTADO(e)}</option>)}
          </select>
        </div>
        <table>
          <thead><tr><th>Código</th><th>Prioridad</th><th>Estado</th><th>Criterio</th><th>Recibida</th></tr></thead>
          <tbody>
            {lista.map((s) => (
              <tr key={s.id} onClick={() => abrir(s.id)} className={detalle?.id === s.id ? "seleccionada" : ""}>
                <td><strong>{s.codigo}</strong></td>
                <td><span className={`prioridad prioridad-${s.prioridad.toLowerCase()}`}>{PRIORIDAD[s.prioridad]}</span></td>
                <td><span className={`estado estado-${s.estado.toLowerCase()}`}>{ESTADO(s.estado)}</span></td>
                <td>{s.regla} · {s.nombre_regla}</td>
                <td>{fecha(s.creada_en)}</td>
              </tr>
            ))}
            {lista.length === 0 && <tr><td colSpan={5} className="tenue">No hay solicitudes con estos filtros.</td></tr>}
          </tbody>
        </table>
      </section>

      <section className="detalle">
        {!detalle ? <p className="tenue">Seleccione una solicitud para ver su detalle. Cada consulta queda registrada en la bitácora de accesos.</p> : (
          <>
            <div className="fila-entre">
              <h2>{detalle.codigo}</h2>
              <span className={`prioridad prioridad-${detalle.prioridad.toLowerCase()}`}>{PRIORIDAD[detalle.prioridad]}</span>
            </div>
            <div className="tarjeta">
              <h4>Contacto</h4>
              <p><strong>{detalle.contacto.nombre}</strong></p>
              <p>{detalle.contacto.correo}{detalle.contacto.telefono ? ` · ${detalle.contacto.telefono}` : ""}</p>
              <p className="tenue">Preferencia: {detalle.contacto.preferencia} · Disponibilidad: {detalle.contacto.disponibilidad}</p>
              <p className="tenue">Base: {detalle.contacto.base_legal}</p>
              {detalle.nota && <blockquote>{detalle.nota}</blockquote>}
            </div>
            <div className="tarjeta">
              <h4>Motivo de la canalización</h4>
              <p>{detalle.resumen.regla} · {detalle.resumen.nombre_regla} <span className="tenue">(reglas v{detalle.resumen.version_reglas})</span></p>
              {detalle.resumen.descripcion_riesgo && <p className="alerta">Señal de riesgo: {detalle.resumen.descripcion_riesgo}</p>}
              {(detalle.resumen.phq9_total != null || detalle.resumen.gad7_total != null) && (
                <p>Tamizaje: {detalle.resumen.phq9_total != null && `PHQ-9 = ${detalle.resumen.phq9_total}`} {detalle.resumen.gad7_total != null && ` · GAD-7 = ${detalle.resumen.gad7_total}`}</p>
              )}
              {detalle.resumen.indicadores.length > 0 && (
                <ul className="indicadores">
                  {detalle.resumen.indicadores.map((i: any) => <li key={i.codigo}><code>{i.codigo}</code> {i.descripcion} <span className="tenue">({i.referencia})</span></li>)}
                </ul>
              )}
              <p className="tenue">Fuentes del criterio: {detalle.resumen.fuentes?.join("; ")}</p>
              <p className="tenue">El sistema no diagnostica: este resumen solo explica por qué se generó la solicitud.</p>
            </div>
            <div className="tarjeta">
              <h4>Seguimiento</h4>
              <ol className="linea-tiempo">
                {detalle.historial.map((h: any, i: number) => (
                  <li key={i}><strong>{ESTADO(h.estado_nuevo)}</strong> · {h.actor} · {fecha(h.fecha)}{h.comentario && <><br /><span className="tenue">{h.comentario}</span></>}</li>
                ))}
              </ol>
              {detalle.transiciones_permitidas.length > 0 && (
                <div className="cambio-estado">
                  <select value={nuevoEstado} onChange={(e) => setNuevoEstado(e.target.value)}>
                    {detalle.transiciones_permitidas.map((t: string) => <option key={t} value={t}>{ESTADO(t)}</option>)}
                  </select>
                  <input placeholder="Comentario (opcional)" value={comentario} onChange={(e) => setComentario(e.target.value)} />
                  <button className="btn-primario" onClick={cambiar}>Actualizar</button>
                </div>
              )}
              {error && <p className="error">{error}</p>}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
