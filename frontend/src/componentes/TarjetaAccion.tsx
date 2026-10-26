import { Accion } from "../api";
import { TarjetaRecurso } from "./Recursos";

interface Props {
  accion: Accion;
  resuelta?: boolean;
  onTamizaje: () => void;
  onDerivacion: () => void;
  onRechazo: (tipo: "TAMIZAJE" | "DERIVACION") => void;
  onVerificacion: (r: "SI" | "NO" | "SIN_RESPUESTA") => void;
}

// Tarjetas que la capa de canalización agrega a la conversación. Sus textos son
// plantillas fijas (no generadas por el modelo de lenguaje).
export default function TarjetaAccion({ accion, resuelta, onTamizaje, onDerivacion, onRechazo, onVerificacion }: Props) {
  if (!accion.texto && accion.recursos.length === 0) return null;
  const riesgo = accion.tipo === "PROTOCOLO_RIESGO";
  return (
    <div className={`tarjeta-accion ${riesgo ? "riesgo" : ""} ${accion.tipo === "VERIFICAR_RIESGO" ? "verificar" : ""}`}>
      {accion.texto && <p>{accion.texto}</p>}

      {!resuelta && accion.tipo === "OFRECER_TAMIZAJE" && (
        <div className="acciones">
          <button className="btn-primario" onClick={onTamizaje}>Responder el cuestionario</button>
          <button className="btn-secundario" onClick={() => onRechazo("TAMIZAJE")}>Ahora no</button>
        </div>
      )}
      {!resuelta && accion.tipo === "OFRECER_DERIVACION" && (
        <div className="acciones">
          <button className="btn-primario" onClick={onDerivacion}>Sí, quiero que me contacten</button>
          <button className="btn-secundario" onClick={() => onRechazo("DERIVACION")}>Ahora no</button>
        </div>
      )}
      {!resuelta && accion.tipo === "VERIFICAR_RIESGO" && (
        <div className="acciones">
          <button className="btn-secundario" onClick={() => onVerificacion("SI")}>Sí</button>
          <button className="btn-secundario" onClick={() => onVerificacion("NO")}>No</button>
          <button className="btn-texto" onClick={() => onVerificacion("SIN_RESPUESTA")}>Prefiero no responder</button>
        </div>
      )}
      {accion.solicitud_codigo && riesgo && (
        <p className="tenue">Código de seguimiento: <strong>{accion.solicitud_codigo}</strong></p>
      )}
      {accion.recursos.length > 0 && (
        <div className="recursos-en-linea">
          {accion.recursos.map((r) => <TarjetaRecurso key={r.id} r={r} />)}
        </div>
      )}
    </div>
  );
}
