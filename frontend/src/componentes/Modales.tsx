import { FormEvent, useEffect, useState } from "react";
import { Accion, api } from "../api";

function Modal({ titulo, children, onCerrar }: { titulo: string; children: React.ReactNode; onCerrar: () => void }) {
  return (
    <div className="fondo-modal" role="dialog" aria-modal="true" aria-label={titulo}>
      <div className="modal">
        <div className="modal-cab"><h2>{titulo}</h2><button className="btn-texto" onClick={onCerrar}>Cerrar</button></div>
        {children}
      </div>
    </div>
  );
}

interface Instrumento {
  instrumento: string; nombre: string; nombre_tecnico: string; instruccion: string;
  items: string[]; opciones: { valor: number; texto: string }[];
}

// Cuestionario voluntario en dos partes (PHQ-9 y GAD-7). Las respuestas se envían
// juntas al final para que el motor emita una sola decisión con ambos puntajes.
export function ModalTamizaje({ onCerrar, onResultado }: { onCerrar: () => void; onResultado: (a: Accion) => void }) {
  const [paso, setPaso] = useState<"PHQ9" | "GAD7">("PHQ9");
  const [def, setDef] = useState<Instrumento | null>(null);
  const [resp, setResp] = useState<number[]>([]);
  const [phq9, setPhq9] = useState<number[] | null>(null);

  useEffect(() => {
    setResp([]);
    api<Instrumento>(`/api/estudiante/instrumentos/${paso}`).then(setDef);
  }, [paso]);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    if (paso === "PHQ9") { setPhq9(resp); setPaso("GAD7"); return; }
    onResultado(await api<Accion>("/api/estudiante/tamizajes", { cuerpo: { phq9, gad7: resp } }));
  };

  if (!def) return null;
  const completo = def.items.every((_, i) => resp[i] !== undefined);
  return (
    <Modal titulo="Cuestionario breve de bienestar" onCerrar={onCerrar}>
      <p className="tenue">{paso === "PHQ9" ? "Parte 1 de 2" : "Parte 2 de 2"} · {def.nombre_tecnico} · Es voluntario: puedes cerrarlo cuando quieras y no se guardará nada.</p>
      <p><strong>{def.instruccion}</strong></p>
      <form onSubmit={enviar} className="tamizaje">
        {def.items.map((item, i) => (
          <fieldset key={`${paso}-${i}`}>
            <legend>{i + 1}. {item}</legend>
            <div className="opciones">
              {def.opciones.map((o) => (
                <label key={o.valor} className={resp[i] === o.valor ? "elegida" : ""}>
                  <input type="radio" name={`${paso}-${i}`} checked={resp[i] === o.valor}
                    onChange={() => { const n = [...resp]; n[i] = o.valor; setResp(n); }} />
                  {o.texto}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        <button className="btn-primario" disabled={!completo}>{paso === "PHQ9" ? "Continuar" : "Enviar respuestas"}</button>
      </form>
    </Modal>
  );
}

export function ModalDerivacion({ onCerrar, onListo }: { onCerrar: () => void; onListo: (codigo: string) => void }) {
  const [f, setF] = useState({ preferencia: "CORREO", telefono: "", disponibilidad: "", nota: "" });
  const [consiento, setConsiento] = useState(false);
  const [error, setError] = useState("");
  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const r = await api<{ codigo: string }>("/api/estudiante/solicitudes", {
        cuerpo: { ...f, telefono: f.telefono || null, nota: f.nota || null, consiento_contacto: consiento } });
      onListo(r.codigo);
    } catch (err) { setError((err as Error).message); }
  };
  return (
    <Modal titulo="Solicitar que me contacten" onCerrar={onCerrar}>
      <p className="tenue">Una persona del equipo de atención psicológica de la universidad se comunicará contigo. Solo verá tu nombre, tus datos de contacto y un resumen general; nunca tus conversaciones.</p>
      <form onSubmit={enviar} className="formulario">
        <label>¿Cómo prefieres que te contacten?
          <select value={f.preferencia} onChange={(e) => setF({ ...f, preferencia: e.target.value })}>
            <option value="CORREO">Correo electrónico</option>
            <option value="TELEFONO">Llamada telefónica</option>
            <option value="WHATSAPP">WhatsApp</option>
          </select>
        </label>
        {f.preferencia !== "CORREO" && (
          <label>Teléfono<input value={f.telefono} onChange={(e) => setF({ ...f, telefono: e.target.value })} /></label>
        )}
        <label>¿En qué horarios estás disponible?
          <input required minLength={3} value={f.disponibilidad} placeholder="Ej.: lunes a jueves por la tarde"
            onChange={(e) => setF({ ...f, disponibilidad: e.target.value })} /></label>
        <label>¿Quieres agregar algo para la persona que te atenderá? (opcional)
          <textarea maxLength={500} value={f.nota} onChange={(e) => setF({ ...f, nota: e.target.value })} /></label>
        <label className="casilla"><input type="checkbox" checked={consiento} onChange={(e) => setConsiento(e.target.checked)} />
          Autorizo compartir mi nombre y datos de contacto con el equipo de atención psicológica.</label>
        {error && <p className="error">{error}</p>}
        <button className="btn-primario" disabled={!consiento}>Enviar solicitud</button>
      </form>
    </Modal>
  );
}
