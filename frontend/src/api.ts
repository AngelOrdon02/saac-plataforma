// Cliente HTTP de la API. El token se guarda en sessionStorage (se borra al
// cerrar la pestaña); si el navegador lo bloquea, se mantiene solo en memoria.
let tokenEnMemoria: string | null = null;

export function guardarSesion(token: string, rol: string, nombre: string) {
  tokenEnMemoria = token;
  try {
    sessionStorage.setItem("saac", JSON.stringify({ token, rol, nombre }));
  } catch { /* almacenamiento no disponible */ }
}

export function leerSesion(): { token: string; rol: string; nombre: string } | null {
  try {
    const s = sessionStorage.getItem("saac");
    if (s) { const d = JSON.parse(s); tokenEnMemoria = d.token; return d; }
  } catch { /* almacenamiento no disponible */ }
  return null;
}

export function cerrarSesion() {
  tokenEnMemoria = null;
  try { sessionStorage.removeItem("saac"); } catch { /* nada */ }
}

export async function api<T = any>(ruta: string, opciones: { metodo?: string; cuerpo?: unknown } = {}): Promise<T> {
  const r = await fetch(ruta, {
    method: opciones.metodo ?? (opciones.cuerpo ? "POST" : "GET"),
    headers: {
      "Content-Type": "application/json",
      ...(tokenEnMemoria ? { Authorization: `Bearer ${tokenEnMemoria}` } : {}),
    },
    body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined,
  });
  if (r.status === 204) return undefined as T;
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof datos.detail === "string" ? datos.detail : "Error de comunicación con el servidor");
  return datos as T;
}

export interface Recurso {
  id: number; nombre: string; tipo: "INSTITUCIONAL" | "LINEA_APOYO" | "EMERGENCIA";
  descripcion: string; ubicacion?: string; horario?: string; telefono?: string;
  enlace?: string; procedimiento?: string;
}

export interface Accion {
  tipo: string; texto?: string | null; recursos: Recurso[]; solicitud_codigo?: string | null;
}

export interface Mensaje {
  id: string; autor: "ESTUDIANTE" | "ASISTENTE"; contenido: string;
  fuentes: { etiqueta: string; titulo: string; referencia: string }[]; creado_en: string;
}

export const fecha = (iso: string) =>
  new Date(iso).toLocaleString("es-GT", { dateStyle: "medium", timeStyle: "short" });
