
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
import base64


import database_controller

router = APIRouter()


@router.get("/get/homescreen/ambientes")
def get_ambientes(db=Depends(database_controller.get_db)):
    try:
        # 1. Query otimizada para PostgreSQL (agregando dias de reserva)
        query = text("""
            SELECT 
                a.ambientes_uid,
                a.nome,
                a.descricao,
                a.capacidade,
                a.capa_mimetype,
                COALESCE(string_agg(DISTINCT to_char(r.data_reserva, 'DD'), ','), '') as dias_indisponiveis
            FROM ambiente a
            LEFT JOIN reservas r 
                ON r.ambientes_uid = a.ambientes_uid
                AND r.status = 'confirmada'
            WHERE a.isactive = 1 AND a.isgeral = 0
            GROUP BY 
                a.ambientes_uid, 
                a.nome, 
                a.descricao, 
                a.capacidade, 
                a.capa_mimetype
        """)

        result = db.execute(query).fetchall()

        ambientes_final = []

        for row in result:
            data = row._mapping
            uid = str(data["ambientes_uid"])

            # 2. Processamento dos dias indisponíveis
            # Converte "01,15,20" em [1, 15, 20]
            dias_str = data["dias_indisponiveis"]
            indisponiveis = [int(d) for d in dias_str.split(',')] if dias_str else []

            # 3. Construção do objeto de retorno
            # Note que a imagem agora aponta para a rota de streaming de fotos
            ambientes_final.append({
                "id": uid,
                "nome": data["nome"],
                "desc": data["descricao"],
                "capacidade": data["capacidade"],
                "img": f"/get/ambiente/foto/{uid}",  # Rota de alta performance
                "indisponiveis": indisponiveis
            })

        return ambientes_final

    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao carregar ambientes")


@router.get("/get/ambiente/foto/{uid}")
def get_foto_ambiente(uid: str, db=Depends(database_controller.get_db)):
    try:
        # 1. Busca os dados. Se o UID for UUID no Postgres, use CAST(:uid AS UUID)
        result = db.execute(
            text("SELECT capa_dados, capa_mimetype FROM ambiente WHERE ambientes_uid = :uid"),
            {"uid": uid}
        ).fetchone()

        if not result or not result[0]:
            return Response(status_code=404)

        foto_blob = result[0]
        mimetype = result[1] or "image/jpeg"

        # 2. Retorno usando argumentos posicionais (mais seguro contra erros de __init__)
        # O primeiro argumento é o corpo da resposta (os bytes)
        return Response(
            bytes(foto_blob),
            media_type=mimetype,
            headers={"Cache-Control": "max-age=86400"}
        )

    except Exception as e:
        print(f"ERRO NA ROTA DE FOTO: {str(e)}")
        # Retornamos o erro real no detalhe para você ver no navegador
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get/homescreen/galeria")
def get_galeria(db=Depends(database_controller.get_db)):
    try:
        # 1. SQL otimizado: Removida a necessidade de dicionário extra se não houver duplicatas
        # Adicionado ORDER BY para respeitar a ordem definida no banco
        query = text("""
            SELECT 
                gal.ambiente_galeria_uid,
                gal.foto_dados,
                gal.foto_mimetype,
                gal.legenda,
                gal.ordem         
            FROM ambiente_galeria gal
            JOIN ambiente amb ON amb.ambientes_uid = gal.ambientes_uid 
            WHERE amb.isgeral = 1 AND amb.isactive = 1
            ORDER BY ordem ASC
        """)

        result = db.execute(query).fetchall()

        galeria_final = []

        for row in result:
            data = row._mapping

            # 2. Processamento da imagem
            img_base64 = None
            if data["foto_dados"]:
                try:
                    encoded_string = base64.b64encode(data["foto_dados"]).decode("utf-8")
                    img_base64 = f"data:{data['foto_mimetype']};base64,{encoded_string}"
                except Exception:
                    img_base64 = None  # Ou uma imagem de placeholder padrão

            # 3. Estrutura simplificada para o Frontend
            galeria_final.append({
                "id": str(data["ambiente_galeria_uid"]),
                "legenda": data["legenda"],
                "img": img_base64
            })

        return galeria_final

    except Exception as e:
        # Log do erro para debug interno
        print(f"Erro na galeria: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar galeria de imagens")