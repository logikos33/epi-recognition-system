"""
CORREÇÃO ROBUSTA DA AUTO-EXTRAÇÃO

Substituir a função auto_extract_background no api_server.py (linhas 1080-1128)
por esta versão com logging completo e error handling robusto.
"""

def auto_extract_background(video_id, video_path, user_id):
    """
    Thread de extração com error handling completo e logging detalhado.

    Args:
        video_id: ID do vídeo no banco
        video_path: Caminho absoluto do arquivo de vídeo
        user_id: ID do usuário para verificação
    """
    import traceback
    import os
    import shutil
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import subprocess
    from sqlalchemy import text

    logger.info(f"[EXTRACT] ========================================")
    logger.info(f"[EXTRACT] Iniciando extração do vídeo {video_id}")
    logger.info(f"[EXTRACT] Path: {video_path}")

    # Criar NOVA conexão com banco (thread safety)
    from backend.database import SessionLocal
    db_local = SessionLocal()

    try:
        # 1. Verificar se arquivo existe
        if not os.path.exists(video_path):
            logger.error(f"[EXTRACT] ❌ Arquivo NÃO encontrado: {video_path}")
            db_local.execute(text("""
                UPDATE training_videos SET status = 'failed' WHERE id = :video_id
            """), {'video_id': video_id})
            db_local.commit()
            return

        logger.info(f"[EXTRACT] ✅ Arquivo encontrado ({os.path.getsize(video_path)/1024/1024:.1f} MB)")

        # 2. Verificar duplicidade com FOR UPDATE (lock)
        result = db_local.execute(text("""
            SELECT status, duration_seconds, selected_start, selected_end
            FROM training_videos WHERE id = :video_id FOR UPDATE
        """), {'video_id': video_id})

        video_data = result.fetchone()
        if not video_data:
            logger.error(f"[EXTRACT] ❌ Vídeo {video_id} não encontrado no banco")
            return

        current_status = video_data[0]
        if current_status in ('extracting', 'completed'):
            logger.info(f"[EXTRACT] ⚠️  Vídeo já está '{current_status}', ignorando")
            return

        # 3. Marcar como extraindo
        logger.info(f"[EXTRACT] Atualizando status para 'extracting'")
        db_local.execute(text("""
            UPDATE training_videos
            SET status = 'extracting', processed_chunks = 0
            WHERE id = :video_id
        """), {'video_id': video_id})
        db_local.commit()

        # 4. Calcular duração e chunks
        duration = video_data[1] or 60
        start = video_data[2] or 0
        end = video_data[3] or min(duration, 600)
        segment_duration = end - start
        total_chunks = max(1, int(segment_duration / 60) + (1 if segment_duration % 60 > 0 else 0))

        db_local.execute(text("""
            UPDATE training_videos SET total_chunks = :total WHERE id = :video_id
        """), {'total': total_chunks, 'video_id': video_id})
        db_local.commit()

        logger.info(f"[EXTRACT] Duração: {segment_duration}s ({start}s → {end}s)")
        logger.info(f"[EXTRACT] Chunks: {total_chunks}")

        # 5. Criar diretório de output
        output_base = os.path.join(
            os.path.dirname(video_path),
            f"frames_{video_id}"
        )
        os.makedirs(output_base, exist_ok=True)
        logger.info(f"[EXTRACT] Output: {output_base}")

        # 6. Extrair com FFmpeg (paralelo)
        if not shutil.which('ffmpeg'):
            logger.error("[EXTRACT] ❌ FFmpeg NÃO encontrado!")
            raise Exception("FFmpeg not found")

        logger.info("[EXTRACT] ✅ FFmpeg encontrado, iniciando extração paralela")
        total_frames = 0
        max_workers = min(4, total_chunks)

        def extract_one_chunk(chunk_num, chunk_start, chunk_duration):
            """Extrai um chunk usando FFmpeg"""
            chunk_dir = os.path.join(output_base, f"chunk_{chunk_num:02d}")
            os.makedirs(chunk_dir, exist_ok=True)

            cmd = [
                'ffmpeg', '-y',
                '-ss', str(chunk_start),
                '-i', os.path.abspath(video_path),  # PATH ABSOLUTO!
                '-t', str(min(chunk_duration, 60)),
                '-vf', 'fps=1,scale=960:-1',
                '-q:v', '8',
                os.path.join(chunk_dir, f'frame_{chunk_num:02d}_%05d.jpg')
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=180)
            if result.returncode != 0:
                error_msg = result.stderr.decode()[:300] if result.stderr else 'Unknown error'
                logger.error(f"[EXTRACT] ❌ FFmpeg erro chunk {chunk_num}: {error_msg}")
                return 0

            frames = [f for f in os.listdir(chunk_dir) if f.endswith('.jpg')]
            return len(frames)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for chunk in range(total_chunks):
                chunk_start = start + (chunk * 60)
                remaining = segment_duration - (chunk * 60)
                chunk_dur = min(60, remaining)

                future = executor.submit(extract_one_chunk, chunk, chunk_start, chunk_dur)
                futures[future] = chunk

            for future in as_completed(futures):
                chunk_num = futures[future]
                try:
                    frames_count = future.result()
                    total_frames += frames_count

                    # Atualizar progresso
                    db_local.execute(text("""
                        UPDATE training_videos
                        SET processed_chunks = processed_chunks + 1
                        WHERE id = :video_id
                    """), {'video_id': video_id})
                    db_local.commit()

                    logger.info(f"[EXTRACT] Chunk {chunk_num:02d}/{total_chunks}: {frames_count} frames")

                except Exception as e:
                    logger.error(f"[EXTRACT] ❌ Chunk {chunk_num} falhou: {e}")

        logger.info(f"[EXTRACT] ✅ Extração completa: {total_frames} frames extraídos")

        # 7. Registrar frames no banco
        logger.info(f"[EXTRACT] Registrando frames no banco...")
        frame_num = 0
        chunk_dirs = sorted([d for d in os.listdir(output_base) if d.startswith('chunk_')])

        for chunk_dir_name in chunk_dirs:
            chunk_path = os.path.join(output_base, chunk_dir_name)
            if not os.path.isdir(chunk_path):
                continue

            chunk_num = int(chunk_dir_name.replace('chunk_', ''))
            frame_files = sorted([f for f in os.listdir(chunk_path) if f.endswith('.jpg')])

            for frame_file in frame_files:
                frame_path = os.path.join(chunk_path, frame_file)
                frame_id = str(uuid.uuid4())

                db_local.execute(text("""
                    INSERT INTO training_frames (id, video_id, frame_number, chunk_number, storage_path, is_annotated, created_at)
                    VALUES (:id, :video_id, :frame_number, :chunk_num, :path, FALSE, NOW())
                """), {
                    'id': frame_id,
                    'video_id': video_id,
                    'frame_number': frame_num,
                    'chunk_num': chunk_num,
                    'path': frame_path
                })

                frame_num += 1

                # Commit a cada 100 frames
                if frame_num % 100 == 0:
                    db_local.commit()
                    logger.info(f"[EXTRACT] Registrados {frame_num}/{total_frames} frames...")

        db_local.commit()
        logger.info(f"[EXTRACT] ✅ {frame_num} frames registrados no banco")

        # 8. Marcar como concluído
        db_local.execute(text("""
            UPDATE training_videos
            SET status = 'completed', frame_count = :total
            WHERE id = :video_id
        """), {'total': frame_num, 'video_id': video_id})
        db_local.commit()

        logger.info(f"[EXTRACT] ========================================")
        logger.info(f"[EXTRACT] ✅ SUCESSO! {frame_num} frames extraídos e registrados")
        logger.info(f"[EXTRACT] ========================================")

    except Exception as e:
        logger.error(f"[EXTRACT] ========================================")
        logger.error(f"[EXTRACT] ❌ ERRO FATAL: {e}")
        logger.error(f"[EXTRACT] Traceback:")
        logger.error(traceback.format_exc())
        logger.error(f"[EXTRACT] ========================================")

        # Marcar como failed
        try:
            db_local.execute(text("""
                UPDATE training_videos SET status = 'failed' WHERE id = :video_id
            """), {'video_id': video_id})
            db_local.commit()
            logger.info(f"[EXTRACT] Status atualizado para 'failed'")
        except Exception as db_err:
            logger.error(f"[EXTRACT] Erro ao atualizar status: {db_err}")

    finally:
        db_local.close()
        logger.info(f"[EXTRACT] Conexão com banco fechada")
