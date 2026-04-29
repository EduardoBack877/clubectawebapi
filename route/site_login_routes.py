import secrets
from datetime import timedelta, datetime

import bcrypt

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

import database_controller
import jwt_utils
from jwt_utils import create_access_token

router = APIRouter()


class RegisterPayload(BaseModel):
    email: str
    password: str
    name: str
    sex: str
    phone: str
    documento: str

from sqlalchemy import text, INTEGER


@router.post("/auth/register")
def register(data: RegisterPayload, db=Depends(database_controller.get_db)):
    try:
        # verifica se já existe
        result = db.execute(
            text("SELECT id FROM usuario WHERE email = :email"),
            {"email": data.email}
        )

        if result.fetchone():
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")

        if(data.sex == "M"):
            sex = 1
        else:
            sex = 0


        senha_hash = bcrypt.hashpw(
            data.password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        db.execute(text("""
            INSERT INTO usuario (
                email,
                senha,
                nome,
                isfeminino,
                isvisitante,
                isactive,
                telefone,
                document
            )
            VALUES (:email, :senha, :nome, :sex, 1, 1, :telefone, :documento)
        """), {
            "email": data.email,
            "senha": senha_hash,
            "nome": data.name,
            "sex":  sex,
            "telefone": data.phone,
            "documento": data.documento

        })

        db.commit()

        return {"message": "Usuário criado com sucesso"}

    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(status_code=500, detail=str(e))


class LoginPayload(BaseModel):
    email: str
    password: str

class ForgetPayload(BaseModel):
    email: str


@router.post("/auth/login")
def login(data: LoginPayload, db=Depends(database_controller.get_db)):
    try:

        result = db.execute(
            text("SELECT id, nome, senha, isadmin, document, passwordversion, telefone FROM usuario WHERE email = :email"),
            {"email": data.email}
        )
        user = result.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Usuário não encontrado")

        senha_hash = user[2]

        if not bcrypt.checkpw(
            data.password.encode("utf-8"),
            senha_hash.encode("utf-8")
        ):
            raise HTTPException(status_code=400, detail="Senha inválida")



        token = create_access_token({
            "id": user[0],
            "email": data.email,
            "document": user[4],
            "passwordVersion": user[5],
            "isAdmin": user[3],
            "phone": user[6]
        })
        print(user[1])

        return {
            "token": token,
            "name": user[1],
            "id" : user[0],
            "isAdmin": user[3],
            "phone": user[6],
            "type": "bearer"
        }


    except Exception as e:
        print("ERRO LOGIN:", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auth/forgotpassword")
def forgotpassword(data: ForgetPayload, db=Depends(database_controller.get_db)):
    try:
        email = data.email
        result = db.execute(
            text("SELECT id, nome FROM usuario WHERE email = :email"),
            {"email": data.email}
        ).fetchone()

        print("Resultado da consulta de existir usuario: ", result, "email: ", data.email)
        if not result:
            raise HTTPException(status_code=400, detail="Usuário não encontrado")

        usuario_id = result[0]
        usuario_nome = result[1]

        # ── Gera token de redefinição (válido por 1h) ──
        token = secrets.token_urlsafe(32)
        expiracao = datetime.utcnow() + timedelta(minutes=10)

        db.execute(
            text("""
                INSERT INTO recuperarsenha (email, token, createdate, isactive, createuserid)
                VALUES (:email, :token, NOW(), 1, :userid)
            """),
            {"email": email, "token": token, "userid": usuario_id}
        )

        # Invalida tokens anteriores do mesmo usuário (boa prática)
        db.execute(
            text("""
                UPDATE recuperarsenha
                SET isactive = 0, changedate = NOW(), changeuserid = :userid
                WHERE email = :email
                  AND isactive = 1
                  AND token != :token
            """),
            {"email": email, "token": token, "userid": usuario_id}
        )

        db.commit()

        reset_link = f"https://seusite.com.br/ambiente/login?view=reset&token={token}"

        # ── Corpo do email HTML ──
        body = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="UTF-8"/>
          <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        </head>
        <body style="margin:0;padding:0;background:#f0f8ff;font-family:'Segoe UI',Arial,sans-serif;">

          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f8ff;padding:40px 0;">
            <tr>
              <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

                  <!-- HEADER -->
                  <tr>
                    <td style="background:linear-gradient(135deg,#006994,#0096C7);border-radius:16px 16px 0 0;padding:40px;text-align:center;">
                      <img src="https://seusite.com.br/imagens/logo.png" alt="AFCTA" height="60"
                           style="margin-bottom:16px;border-radius:8px;"
                           onerror="this.style.display='none'"/>
                      <h1 style="color:#ffffff;font-size:26px;margin:0;font-weight:800;letter-spacing:-0.5px;">
                        Redefinição de Senha
                      </h1>
                      <p style="color:rgba(255,255,255,0.75);font-size:14px;margin:8px 0 0;">
                        AFCTA — Associação dos Colaboradores CTA
                      </p>
                    </td>
                  </tr>

                  <!-- BODY -->
                  <tr>
                    <td style="background:#ffffff;padding:40px;">

                      <p style="color:#0A3D52;font-size:16px;margin:0 0 8px;">
                        Olá, <strong>{usuario_nome}</strong> 👋
                      </p>
                      <p style="color:#3A7CA5;font-size:15px;line-height:1.7;margin:0 0 28px;">
                        Recebemos uma solicitação para redefinir a senha da sua conta AFCTA.
                        Clique no botão abaixo para criar uma nova senha.
                      </p>

                      <!-- BOTÃO CTA -->
                      <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td align="center" style="padding:8px 0 32px;">
                            <a href="{reset_link}"
                               style="display:inline-block;background:linear-gradient(135deg,#FFD166,#FF9F1C);
                                      color:#0A3D52;text-decoration:none;padding:16px 44px;
                                      border-radius:50px;font-weight:800;font-size:15px;
                                      letter-spacing:0.3px;box-shadow:0 6px 20px rgba(255,159,28,0.35);">
                              🔑 Redefinir minha senha
                            </a>
                          </td>
                        </tr>
                      </table>

                      <!-- AVISO DE EXPIRAÇÃO -->
                      <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                          <td style="background:#FFF8EE;border-left:4px solid #FF9F1C;
                                     border-radius:0 10px 10px 0;padding:14px 18px;margin-bottom:28px;">
                            <p style="color:#0A3D52;font-size:13px;margin:0;font-weight:700;">
                              ⏰ Este link expira em <strong>10 minutos</strong>.
                            </p>
                            <p style="color:#3A7CA5;font-size:12px;margin:6px 0 0;">
                              Após esse prazo, você precisará solicitar um novo link de redefinição.
                            </p>
                          </td>
                        </tr>
                      </table>

                      <p style="color:#3A7CA5;font-size:13px;line-height:1.7;margin:24px 0 0;">
                        Se você <strong>não solicitou</strong> a redefinição de senha, ignore este e-mail.
                        Sua senha atual permanece inalterada e sua conta está segura.
                      </p>
                    </td>
                  </tr>

                  <!-- FOOTER -->
                  <tr>
                    <td style="background:#006994;border-radius:0 0 16px 16px;padding:24px 40px;text-align:center;">
                      <p style="color:rgba(255,255,255,0.5);font-size:12px;margin:0;">
                        © 2026 AFCTA — Associação dos Colaboradores CTA<br/>
                        Acesso Imperatriz Dona Leopoldina, 3154 — Venâncio Aires/RS
                      </p>
                    </td>
                  </tr>

                </table>
              </td>
            </tr>
          </table>

        </body>
        </html>
        """

        # ── Dispara o email ──
      # ajuste conforme sua instância
        email_service = EmailService()
        email_service.send_email(
            subject="🔑 Redefinição de senha — AFCTA",
            body=body,
            recipients=[email]
        )

        return {"message": "E-mail de redefinição enviado com sucesso."}

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO FORGOT PASSWORD:", e)
        raise HTTPException(status_code=500, detail=str(e))


class ResetTokenPayload(BaseModel):
    token: str


@router.post("/auth/validateresettoken")
def validate_reset_token(data: ResetTokenPayload, db=Depends(database_controller.get_db)):
    try:
        row = db.execute(
            text("""
                SELECT r.recuperarsenha_uid, r.email, r.createdate, u.id as usuario_id
                FROM recuperarsenha r
                INNER JOIN usuario u ON u.email = r.email
                WHERE r.token    = :token
                  AND r.isactive = 1
            """),
            {"token": data.token}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Token inválido ou já utilizado.")

        if datetime.utcnow() - row.createdate > timedelta(hours=1):
            # Invalida automaticamente se expirado
            db.execute(
                text("""
                    UPDATE recuperarsenha
                    SET isactive     = 0,
                        changedate   = NOW(),
                        changeuserid = :userid
                    WHERE token = :token
                """),
                {"token": data.token, "userid": row.usuario_id}
            )
            db.commit()
            raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo link.")

        return {
            "valid":    True,
            "email":    row.email,
            "userid":   row.usuario_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO VALIDATE RESET TOKEN:", e)
        raise HTTPException(status_code=500, detail=str(e))



from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ResetPasswordPayload(BaseModel):
    token:        str
    nova_senha:   str

    @field_validator("nova_senha")
    @classmethod
    def senha_valida(cls, v):
        if len(v) < 8:
            raise ValueError("A senha deve ter no mínimo 8 caracteres.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 caracteres.")
        return v

@router.post("/auth/resetpassword")
def reset_password(data: ResetPasswordPayload, db=Depends(database_controller.get_db)):
    try:
        row = db.execute(
            text("""
                SELECT r.recuperarsenha_uid, r.email, r.createdate, u.id as usuario_id
                FROM recuperarsenha r
                INNER JOIN usuario u ON u.email = r.email
                WHERE r.token    = :token
                  AND r.isactive = 1
            """),
            {"token": data.token}
        ).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Token inválido ou já utilizado.")

        if datetime.utcnow() - row.createdate > timedelta(minutes=10):
            raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo link.")


        # ✅ Trunca para 72 bytes antes de hashear
        senha_bytes = data.nova_senha.encode("utf-8")[:72]
        senha_hash = bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")
        db.execute(
            text("""
                UPDATE usuario
                SET senha        = :senha,
                    changedate   = NOW(),
                    changeuserid = :userid
                WHERE id = :userid
            """),
            {"senha": senha_hash, "userid": row.usuario_id}
        )

        # Invalida o token usado
        db.execute(
            text("""
                UPDATE recuperarsenha
                SET isactive     = 0,
                    changedate   = NOW(),
                    changeuserid = :userid
                WHERE token = :token
            """),
            {"token": data.token, "userid": row.usuario_id}
        )

        db.commit()
        return {"message": "Senha redefinida com sucesso."}

    except HTTPException:
        raise
    except Exception as e:
        print("ERRO RESET PASSWORD:", e)
        raise HTTPException(status_code=500, detail=str(e))


#--------------------------------------
# PARTE DA API DE ENVIAR O EMAIL
#--------------------------------------
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

class EmailService:
    SMTP_HOST = "smtp.gmail.com"
    SMTP_PORT = 587
    USERNAME = "notificacaoafcta@gmail.com"
    PASSWORD = "noybdotkoxrtcukz"

    def __init__(self):
        self.server = smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT)
        self.server.starttls()
        self.server.login(self.USERNAME, self.PASSWORD)

    def send_email(self, subject, body, recipients, attachment_path=None):
        msg = MIMEMultipart()
        msg['From'] = self.USERNAME
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject

        # Corpo do e-mail em HTML
        msg.attach(MIMEText(body, 'html'))

        # Adicionar anexo, se houver
        if attachment_path:
            try:
                with open(attachment_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                    msg.attach(part)
            except Exception as e:
                print(f"Erro ao anexar o arquivo: {e}")
                raise

        # Enviar o e-mail
        try:
            self.server.sendmail(self.USERNAME, recipients, msg.as_string())
            print("E-mail enviado com sucesso!")
        except Exception as e:
            print(f"Erro ao enviar o e-mail: {e}")
            raise

    def __del__(self):
        # Fechar a conexão SMTP se ela estiver aberta
        if self.server is not None:
            try:
                self.server.quit()
            except Exception as e:
                print(f"Erro ao fechar a conexão SMTP: {e}")

