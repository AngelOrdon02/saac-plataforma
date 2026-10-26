import { FormEvent, useEffect, useState } from "react";
import { api, guardarSesion } from "../api";

type Sesion = { token: string; rol: string; nombre: string };

export default function Ingreso({ alIngresar }: { alIngresar: (s: Sesion) => void }) {
  const [modo, setModo] = useState<"ingreso" | "registro">("ingreso");
  const [form, setForm] = useState({ nombre: "", correo: "", contrasena: "", telefono: "" });
  const [acepta, setAcepta] = useState(false);
  const [consentimiento, setConsentimiento] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<{ texto: string }>("/api/auth/consentimiento").then((d) => setConsentimiento(d.texto)).catch(() => {});
  }, []);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const s = modo === "ingreso"
        ? await api<Sesion>("/api/auth/ingreso", { cuerpo: { correo: form.correo, contrasena: form.contrasena } })
        : await api<Sesion>("/api/auth/registro", {
            cuerpo: { ...form, telefono: form.telefono || null, acepta_consentimiento: acepta } });
      guardarSesion(s.token, s.rol, s.nombre);
      alIngresar(s);
    } catch (err) { setError((err as Error).message); }
  };

  const campo = (k: keyof typeof form) => ({
    value: form[k], onChange: (e: any) => setForm({ ...form, [k]: e.target.value }),
  });

  return (
    <main className="ingreso">
      <section className="ingreso-intro">
        <span className="logo grande" aria-hidden>◆</span>
        <h1>Acompañamiento académico</h1>
        <p>Un asistente para organizar tu tiempo y estudiar mejor, con base en evidencia. Y si en algún
          momento necesitas hablar con alguien, te ayudamos a llegar al servicio de atención psicológica
          de la universidad.</p>
        <ul>
          <li>Tus conversaciones se guardan cifradas.</li>
          <li>Nadie del personal puede leerlas.</li>
          <li>Este sistema no diagnostica ni sustituye a un profesional.</li>
        </ul>
      </section>
      <form className="tarjeta ingreso-form" onSubmit={enviar}>
        <div className="pestanas">
          <button type="button" className={modo === "ingreso" ? "activa" : ""} onClick={() => setModo("ingreso")}>Ingresar</button>
          <button type="button" className={modo === "registro" ? "activa" : ""} onClick={() => setModo("registro")}>Crear cuenta</button>
        </div>
        {modo === "registro" && (
          <label>Nombre completo<input required minLength={3} {...campo("nombre")} /></label>
        )}
        <label>Correo<input type="email" required {...campo("correo")} /></label>
        <label>Contraseña<input type="password" required minLength={modo === "registro" ? 10 : 1} {...campo("contrasena")} /></label>
        {modo === "registro" && (
          <>
            <label>Teléfono (opcional)<input {...campo("telefono")} placeholder="Para que puedan contactarte si lo solicitas" /></label>
            <details className="consentimiento">
              <summary>Leer el consentimiento informado</summary>
              <pre>{consentimiento}</pre>
            </details>
            <label className="casilla">
              <input type="checkbox" checked={acepta} onChange={(e) => setAcepta(e.target.checked)} />
              He leído y acepto el consentimiento informado.
            </label>
          </>
        )}
        {error && <p className="error">{error}</p>}
        <button className="btn-primario" disabled={modo === "registro" && !acepta}>
          {modo === "ingreso" ? "Ingresar" : "Crear cuenta"}
        </button>
      </form>
    </main>
  );
}
