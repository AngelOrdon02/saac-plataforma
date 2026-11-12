import { FormEvent, useEffect, useRef, useState } from "react";
import { Accion, Mensaje, Recurso, api, fecha } from "../api";
import PanelRecursos from "../componentes/Recursos";
import TarjetaAccion from "../componentes/TarjetaAccion";
import { ModalDerivacion, ModalTamizaje } from "../componentes/Modales";

interface Conversacion { id: string; titulo: string; actualizada_en: string }
const NOMBRES_ESTADO: Record<string, string> = {
  NUEVA: "Recibida", EN_REVISION: "En revisión", CONTACTADO: "Contactado", AGENDADA: "Cita agendada",
  NO_LOCALIZADO: "No te pudimos localizar", FINALIZADA: "Finalizada", CANCELADA: "Cancelada",
};
type Entrada = { tipo: "mensaje"; m: Mensaje } | { tipo: "accion"; a: Accion; id: string; resuelta?: boolean };

const SUGERENCIAS = [
  "¿Cómo me preparo para un examen parcial?",
  "Tengo muchas entregas esta semana, ¿cómo me organizo?",
  "Siempre dejo todo para el último momento",
];

export default function Estudiante() {
  const [vista, setVista] = useState<"chat" | "solicitudes">("chat");
  const [conversaciones, setConversaciones] = useState<Conversacion[]>([]);
  const [actual, setActual] = useState<string | null>(null);
  const [entradas, setEntradas] = useState<Entrada[]>([]);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [recursos, setRecursos] = useState<Recurso[]>([]);
  const [modal, setModal] = useState<"tamizaje" | "derivacion" | null>(null);
  const [solicitudes, setSolicitudes] = useState<any[]>([]);
  const fin = useRef<HTMLDivElement>(null);

  const cargarConversaciones = () => api<Conversacion[]>("/api/estudiante/conversaciones").then(setConversaciones);
  useEffect(() => {
    cargarConversaciones();
    api<Recurso[]>("/api/recursos").then(setRecursos);
  }, []);
  useEffect(() => { fin.current?.scrollIntoView({ behavior: "smooth" }); }, [entradas]);
  useEffect(() => {
    if (vista === "solicitudes") api<any[]>("/api/estudiante/solicitudes").then(setSolicitudes);
  }, [vista]);

  const abrir = async (id: string) => {
    setActual(id); setVista("chat");
    const ms = await api<Mensaje[]>(`/api/estudiante/conversaciones/${id}/mensajes`);
    setEntradas(ms.map((m) => ({ tipo: "mensaje", m })));
  };

  const nueva = async () => {
    const c = await api<Conversacion>("/api/estudiante/conversaciones", { cuerpo: {} });
    setActual(c.id); setEntradas([]); setVista("chat"); cargarConversaciones();
    return c.id;
  };

  // Una vez que el estudiante responde a una tarjeta, se ocultan sus botones.
  const resolverPendientes = (tipos: string[]) => setEntradas((e) => e.map((x) =>
    x.tipo === "accion" && tipos.includes(x.a.tipo) ? { ...x, resuelta: true } : x));

  const agregarAccion = (a: Accion) => {
    // El acompañamiento ordinario no trae tarjeta; solo se muestra si incluye un aviso o
    // recursos (por ejemplo, cuando el servicio de modelos no está disponible).
    if (!a.texto && a.recursos.length === 0) return;
    setEntradas((e) => [...e, { tipo: "accion", a, id: crypto.randomUUID() }]);
  };

  const enviar = async (e?: FormEvent, sugerido?: string) => {
    e?.preventDefault();
    const contenido = (sugerido ?? texto).trim();
    if (!contenido || enviando) return;
    setEnviando(true); setTexto("");
    try {
      const id = actual ?? (await nueva());
      const r = await api(`/api/estudiante/conversaciones/${id}/mensajes`, { cuerpo: { texto: contenido } });
      setEntradas((prev) => [...prev, { tipo: "mensaje", m: r.mensaje_estudiante },
        ...(r.respuesta ? [{ tipo: "mensaje" as const, m: r.respuesta }] : [])]);
      agregarAccion(r.accion);
      cargarConversaciones();
    } catch {
      // Falla segura: el mensaje no se pierde y el estudiante ve a quién acudir.
      setTexto(contenido);
      agregarAccion({ tipo: "INFORMACION", recursos,
        texto: "No pudimos procesar tu mensaje en este momento. Inténtalo de nuevo en unos minutos; si necesitas apoyo ahora, puedes acudir a estos servicios:" });
    } finally { setEnviando(false); }
  };

  const rechazar = async (tipo: "TAMIZAJE" | "DERIVACION") => {
    await api("/api/estudiante/ofertas/rechazo", { cuerpo: { tipo } });
    resolverPendientes([tipo === "TAMIZAJE" ? "OFRECER_TAMIZAJE" : "OFRECER_DERIVACION"]);
    agregarAccion({ tipo: "INFORMACION", texto: "Está bien. Si cambias de opinión, los recursos de apoyo siempre están disponibles en el panel de la derecha.", recursos: [] });
  };

  const verificar = async (respuesta: "SI" | "NO" | "SIN_RESPUESTA") => {
    resolverPendientes(["VERIFICAR_RIESGO"]);
    agregarAccion(await api<Accion>("/api/estudiante/verificacion", { cuerpo: { respuesta } }));
  };

  const cancelar = async (codigo: string) => {
    await api(`/api/estudiante/solicitudes/${codigo}/cancelar`, { cuerpo: {} });
    setSolicitudes(await api<any[]>("/api/estudiante/solicitudes"));
  };

  return (
    <div className="estudiante">
      <nav className="lateral">
        <button className="btn-primario ancho" onClick={nueva}>+ Nueva conversación</button>
        <button className={`enlace-lateral ${vista === "solicitudes" ? "activo" : ""}`} onClick={() => setVista("solicitudes")}>Mis solicitudes</button>
        <h4>Conversaciones</h4>
        {conversaciones.map((c) => (
          <button key={c.id} className={`enlace-lateral ${c.id === actual && vista === "chat" ? "activo" : ""}`} onClick={() => abrir(c.id)}>
            {c.titulo}<small>{fecha(c.actualizada_en)}</small>
          </button>
        ))}
      </nav>

      {vista === "chat" ? (
        <section className="chat">
          <div className="mensajes">
            {entradas.length === 0 && (
              <div className="bienvenida">
                <h2>¿En qué te puedo ayudar hoy?</h2>
                <p className="tenue">Puedo orientarte sobre técnicas de estudio, organización del tiempo y cómo preparar tus evaluaciones.</p>
                <div className="sugerencias">
                  {SUGERENCIAS.map((s) => <button key={s} onClick={() => enviar(undefined, s)}>{s}</button>)}
                </div>
              </div>
            )}
            {entradas.map((e) => e.tipo === "mensaje" ? (
              <div key={e.m.id} className={`burbuja ${e.m.autor === "ESTUDIANTE" ? "propia" : "asistente"}`}>
                <div className="contenido">{e.m.contenido}</div>
                {e.m.fuentes?.length > 0 && (
                  <div className="fuentes">Fuentes: {e.m.fuentes.map((f) => `[${f.etiqueta}] ${f.titulo} (${f.referencia})`).join(" · ")}</div>
                )}
              </div>
            ) : (
              <TarjetaAccion key={e.id} accion={e.a} resuelta={e.resuelta} onTamizaje={() => setModal("tamizaje")}
                onDerivacion={() => setModal("derivacion")} onRechazo={rechazar} onVerificacion={verificar} />
            ))}
            {enviando && <div className="burbuja asistente escribiendo">Escribiendo…</div>}
            <div ref={fin} />
          </div>
          <form className="entrada" onSubmit={enviar}>
            <textarea value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe tu consulta…" rows={2}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }} />
            <button className="btn-primario" disabled={enviando || !texto.trim()}>Enviar</button>
          </form>
          <p className="aviso">Este asistente no realiza diagnósticos ni sustituye la atención de un profesional.</p>
        </section>
      ) : (
        <section className="solicitudes-estudiante">
          <h2>Mis solicitudes de atención</h2>
          {solicitudes.length === 0 && <p className="tenue">No tienes solicitudes registradas.</p>}
          {solicitudes.map((s) => (
            <div key={s.codigo} className="tarjeta">
              <div className="fila-entre"><strong>{s.codigo}</strong><span className={`estado estado-${s.estado.toLowerCase()}`}>{NOMBRES_ESTADO[s.estado]}</span></div>
              <ol className="linea-tiempo">
                {s.historial.map((h: any, i: number) => <li key={i}>{NOMBRES_ESTADO[h.estado]} · {fecha(h.fecha)}</li>)}
              </ol>
              {s.cancelable && <button className="btn-texto" onClick={() => cancelar(s.codigo)}>Cancelar solicitud</button>}
            </div>
          ))}
        </section>
      )}

      <PanelRecursos recursos={recursos} />

      {modal === "tamizaje" && <ModalTamizaje onCerrar={() => setModal(null)} onResultado={(a) => { setModal(null); resolverPendientes(["OFRECER_TAMIZAJE"]); agregarAccion(a); }} />}
      {modal === "derivacion" && <ModalDerivacion onCerrar={() => setModal(null)} onListo={(codigo) => {
        setModal(null);
        resolverPendientes(["OFRECER_DERIVACION"]);
        agregarAccion({ tipo: "INFORMACION", texto: `Listo. Registramos tu solicitud ${codigo}. El equipo de atención psicológica te contactará según tus preferencias. Puedes ver el avance en «Mis solicitudes».`, recursos: [] });
      }} />}
    </div>
  );
}
