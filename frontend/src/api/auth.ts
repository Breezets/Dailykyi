import request from "./request";

export async function getQrCode(): Promise<{ qrcode_key: string; qrcode_url: string }> {
  return request.get<unknown, { qrcode_key: string; qrcode_url: string }>("/auth/qr");
}

export async function getQrStatus(qrcodeKey: string): Promise<{ status: string; message?: string; uid?: number }> {
  return request.get<unknown, { status: string; message?: string; uid?: number }>("/auth/qr/status", {
    params: { qrcode_key: qrcodeKey },
  });
}

export async function cookieLogin(cookie: string): Promise<{ status: string; message: string; uid: number }> {
  return request.post<unknown, { status: string; message: string; uid: number }>("/auth/cookie-login", { cookie });
}
