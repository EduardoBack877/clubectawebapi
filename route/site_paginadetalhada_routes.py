from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy import text
import base64
import uuid
from datetime import date, time
from typing import Optional

# Assumindo que database_controller.py existe e contém get_db
import database_controller


# --- Modelos Pydantic ---
class ReservaCreate(BaseModel):
    ambientes_uid: str  # O frontend envia o UUID do ambiente
    usuarioid: int
    data_reserva: date
    hora_inicio: time
    hora_fim: time
    status: Optional[str] = "confirmada"
    observacoes: Optional[str] = None


class Reserva(ReservaCreate):
    reservas_uid: str  # UUID gerado pelo banco de dados
    createuserid: Optional[int] = None
    changeuserid: Optional[int] = None
    createdate: Optional[str] = None  # Ou datetime, dependendo da formatação
    changedate: Optional[str] = None  # Ou datetime, dependendo da formatação


class ReservaUpdate(BaseModel):
    data_reserva: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    status: Optional[str] = None
    observacoes: Optional[str] = None


# --- Rotas FastAPI ---
router = APIRouter()


@router.get("/ambientes/{ambiente_id}/capa")
def get_capa(ambiente_id: str, db=Depends(database_controller.get_db)):
    try:
        result = db.execute(text("""
            SELECT capa_dados, capa_mimetype
            FROM ambiente
            WHERE ambientes_uid = :id
        """), {"id": ambiente_id}).fetchone()

        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")

        capa_dados, capa_mimetype = result

        return Response(
            content=capa_dados,
            media_type=capa_mimetype
        )

    except Exception as e:
        print("🔥 ERRO BACKEND:", e)
        return {"erro": str(e)}


@router.get("/api/ambientes/{ambientes_uid}/reservas")
def get_reservas(ambientes_uid: str, db=Depends(database_controller.get_db)):
    try:
        sql = text("""
            SELECT 
                reservas_uid,
                data_reserva,
                hora_inicio,
                hora_fim,
                status
            FROM RESERVAS
            WHERE ambientes_uid = :id
        """)

        result = db.execute(sql, {"id": ambientes_uid}).fetchall()

        if not result:
            return []
        return [
            {
                "reservas_uid": str(r[0]),
                "data_reserva": str(r[1]),
                "hora_inicio": str(r[2])[:5],
                "hora_fim": str(r[3])[:5],
                "status": r[4],
            }
            for r in result
        ]
    except Exception as e:
        print(f"Erro ao buscar reservas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@router.get("/api/galeria/{ambientes_uid}")
def get_galeria(ambientes_uid: str, db=Depends(database_controller.get_db)):
    try:
        sql = text("""
            SELECT 
                ambiente_galeria_uid,
                foto_dados,
                foto_mimetype,
                legenda,
                ordem
            FROM ambiente_galeria
            WHERE ambientes_uid = :ambientes_uid
            ORDER BY ordem ASC
        """)

        query_result = db.execute(sql, {"ambientes_uid": ambientes_uid}).fetchall()
        if not query_result:
            return []

        return [
            {
                "ambiente_galeria_uid": str(r[0]),
                "foto_dados": base64.b64encode(r[1]).decode("utf-8") if r[1] else None,
                "foto_mimetype": r[2],
                "legenda": r[3],
                "ordem": r[4],
            }
            for r in query_result
        ]

    except Exception as e:
        print(f"Erro ao buscar galeria: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/reservas", response_model=Reserva, status_code=status.HTTP_201_CREATED)
def create_reserva(reserva: ReservaCreate, db=Depends(database_controller.get_db)):
    try:
        print(f"[BACKEND DEBUG] Dados recebidos para reserva: {reserva.dict()}")
        reservas_uid = str(uuid.uuid4())

        ambiente_real_uid = reserva.ambientes_uid
        print(f"[BACKEND DEBUG] UUID do ambiente recebido: {ambiente_real_uid}")

        sql = text("""
            INSERT INTO RESERVAS (
                reservas_uid,
                ambientes_uid,
                usuarioid,
                data_reserva,
                hora_inicio,
                hora_fim,
                status,
                observacoes
            )
            VALUES (
                :reservas_uid,
                :ambientes_uid,
                :usuarioid,
                :data_reserva,
                :hora_inicio,
                :hora_fim,
                :status,
                :observacoes
            )
            RETURNING reservas_uid, ambientes_uid, usuarioid, data_reserva, hora_inicio, hora_fim, status, observacoes, createuserid, changeuserid, createdate, changedate
        """)

        result_proxy = db.execute(sql, {
            "reservas_uid": reservas_uid,
            "ambientes_uid": ambiente_real_uid,
            "usuarioid": reserva.usuarioid,
            "data_reserva": reserva.data_reserva,
            "hora_inicio": reserva.hora_inicio,
            "hora_fim": reserva.hora_fim,
            "status": reserva.status,
            "observacoes": reserva.observacoes,
        })
        db.commit()
        created_reserva_data = result_proxy.mappings().fetchone()
        print(f"[BACKEND DEBUG] Resultado da inserção no DB: {created_reserva_data}")

        if not created_reserva_data:
            print("[BACKEND DEBUG] Inserção no DB retornou vazio.")
            raise HTTPException(status_code=500, detail="Falha ao criar a reserva.")

        # Mapear o resultado usando os nomes das colunas
        created_reserva = Reserva(
            reservas_uid=str(created_reserva_data["reservas_uid"]),
            ambientes_uid=str(created_reserva_data["ambientes_uid"]),
            usuarioid=created_reserva_data["usuarioid"],
            data_reserva=created_reserva_data["data_reserva"],
            hora_inicio=created_reserva_data["hora_inicio"],
            hora_fim=created_reserva_data["hora_fim"],
            status=created_reserva_data["status"],
            observacoes=created_reserva_data["observacoes"],
            createuserid=created_reserva_data["createuserid"],
            changeuserid=created_reserva_data["changeuserid"],
            createdate=str(created_reserva_data["createdate"]) if created_reserva_data["createdate"] else None,
            changedate=str(created_reserva_data["changedate"]) if created_reserva_data["changedate"] else None,
        )

        return created_reserva

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"[BACKEND ERROR] Erro ao criar reserva: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.put("/api/ambientes/{ambientes_uid}/reservas/{reservas_uid}")
def update_reserva(ambientes_uid: str, reservas_uid: str, body: ReservaUpdate, db=Depends(database_controller.get_db)):
    try:
        print(f">>> BODY: {body}")  # <- vai mostrar o que chega

        check = db.execute(
            text("SELECT reservas_uid FROM RESERVAS WHERE reservas_uid = :rid AND ambientes_uid = :aid"),
            {"rid": reservas_uid, "aid": ambientes_uid}
        ).fetchone()

        if not check:
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        # REMOVIDO: validação de horário por enquanto

        campos = {}
        if body.data_reserva is not None:
            campos["data_reserva"] = body.data_reserva
        if body.hora_inicio is not None:
            campos["hora_inicio"] = body.hora_inicio
        if body.hora_fim is not None:
            campos["hora_fim"] = body.hora_fim
        if body.status is not None:
            campos["status"] = body.status
        if body.observacoes is not None:
            campos["observacoes"] = body.observacoes

        if not campos:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        set_clause = ", ".join([f"{k} = :{k}" for k in campos.keys()])
        campos["rid"] = reservas_uid
        campos["aid"] = ambientes_uid

        db.execute(
            text(f"UPDATE RESERVAS SET {set_clause} WHERE reservas_uid = :rid AND ambientes_uid = :aid"),
            campos
        )
        db.commit()

        return {"message": "Reserva atualizada com sucesso", "reservas_uid": reservas_uid}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao atualizar reserva: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# --- DELETE ---
@router.delete("/api/ambientes/{ambientes_uid}/reservas/{reservas_uid}")
def delete_reserva(ambientes_uid: str, reservas_uid: str, db=Depends(database_controller.get_db)):
    try:
        check = db.execute(
            text("SELECT reservas_uid FROM RESERVAS WHERE reservas_uid = :rid AND ambientes_uid = :aid"),
            {"rid": reservas_uid, "aid": ambientes_uid}
        ).fetchone()

        if not check:
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        db.execute(
            text("DELETE FROM RESERVAS WHERE reservas_uid = :rid AND ambientes_uid = :aid"),
            {"rid": reservas_uid, "aid": ambientes_uid}
        )
        db.commit()

        return Response(status_code=204)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Erro ao deletar reserva: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")