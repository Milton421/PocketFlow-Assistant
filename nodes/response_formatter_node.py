import re

class ResponseFormatter:
    def format(self, answer: str, force_bullets: bool = False, is_unified_request: bool = True) -> str:
        """Formatea la respuesta según el tipo de solicitud.
        
        Args:
            answer: Texto a formatear
            force_bullets: Si es True, fuerza el formato de lista
            is_unified_request: Si es True, usa formato de lista unificada. 
                              Si es False, usa párrafos separados por comas.
        """
        print(f"[FORMATTER] Processing: force_bullets={force_bullets}, unified={is_unified_request}")
        print(f"[FORMATTER] Input length: {len(answer)} chars")
        
        if not answer or not isinstance(answer, str):
            return "No se encontró información suficiente"

        answer = self._initial_cleanup(answer)
        
        # Si no es una solicitud unificada, forzar formato narrativo
        if not is_unified_request and not force_bullets:
            return self._format_narrative(answer)
            
        formatting_strategy = self._determine_formatting_strategy(answer, force_bullets or is_unified_request)
        print(f"[FORMATTER] Strategy: {formatting_strategy}")
        
        if formatting_strategy == "hierarchical":
            result = self._format_hierarchical(answer, is_unified_request)
        elif formatting_strategy == "risks_benefits":
            result = self._format_risks_benefits(answer, is_unified_request)
        elif formatting_strategy == "simple_list":
            result = self._format_simple_list(answer) if is_unified_request else self._format_narrative(answer)
        elif formatting_strategy == "mixed_content":
            result = self._format_mixed_content(answer) if is_unified_request else self._format_narrative(answer)
        else:
            result = self._format_narrative(answer)
        
        result = self._final_cleanup(result)
        
        print(f"[FORMATTER] Output length: {len(result)} chars")
        return result

    def _initial_cleanup(self, text: str) -> str:
        """Limpieza inicial del texto"""
        # Remover prefijos redundantes
        text = re.sub(r"^\s*(respuesta|la respuesta)\s*:\s*", "", text, flags=re.I)
        
        # Normalizar espacios, pero PRESERVAR saltos de línea para no destruir listas/párrafos
        text = re.sub(r'[ \t]+', ' ', text)      # solo espacios y tabs
        text = re.sub(r'\n\s*\n+', '\n\n', text) # comprimir múltiples líneas en doble salto

        # Corregir errores de puntuación tipo "Riesgos:."
        text = re.sub(r':\s*\.', ':', text)

        # Eliminar líneas que solo contienen asteriscos (artefactos de OCR/parseo como "**.")
        text = re.sub(r'(?m)^\s*\*{1,3}\s*[.,;:!?]?\s*$', '', text)
        
        # Separar texto pegado común
        text = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)', r'\1. \2', text)
        text = re.sub(r'([.!?])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)
        
        return text.strip()

    def _determine_formatting_strategy(self, text: str, force_bullets: bool) -> str:
        """Determina qué estrategia de formateo usar"""
        
        # Caso especial: secciones de "Riesgos" y "Beneficios"
        if re.search(r'\briesgos?\b\s*:', text, re.IGNORECASE) and re.search(r'\bbeneficios?\b\s*:', text, re.IGNORECASE):
            return "risks_benefits"
        
        # 1. Detectar contenido jerárquico (categorías con subcategorías)
        hierarchical_patterns = [
            r'para el profesor\s*[-:]',
            r'para (?:el alumno|los alumnos)\s*[-:]',
            r'para el trabajo en el aula\s*[-:]',
            r'relacionados con el objeto de estudio',
            r'(?:tipos de|clases de|categorías de)'
        ]
        
        hierarchical_count = sum(1 for pattern in hierarchical_patterns
                                if re.search(pattern, text, re.IGNORECASE))
        
        if hierarchical_count >= 2:
            return "hierarchical"
        
        # 2. Detectar listas simples (más restrictivo: requiere marcadores claros)
        list_indicators = [
            r'\b(?:incluye|incluyen|son|menciona|mencionan|contiene|contienen|enumera|enumeran|presenta|presentan)\b\s*:?',  # verbo+:
            r'^\s*[-•·*]\s+',  # Ya tiene viñetas
            r'^\s*\d+[.)]\s+',  # Ya numerada
        ]
        
        list_count = sum(1 for pattern in list_indicators
                        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE))
        comma_count = text.count(',')
        
        # Solo considerar lista simple si hay fuerza explícita o marcadores claros.
        if force_bullets or list_count >= 1:
            return "simple_list"
        
        # 3. Detectar contenido mixto (párrafos + enumeraciones por comas)
        has_long_sentences = any(len(sent.strip()) > 80 for sent in re.split(r'(?<=[.!?])\s+', text))
        has_short_items = comma_count >= 4
        
        if has_long_sentences and has_short_items:
            return "mixed_content"
        
        # 4. Por defecto: narrativo
        return "narrative"

    def _format_hierarchical(self, text: str, is_unified_request: bool = True) -> str:
        """Formatea contenido jerárquico con categorías claras
        
        Args:
            text: Texto a formatear
            is_unified_request: Si es True, devuelve una lista. Si es False, devuelve párrafos separados por comas.
        """
        print(f"[FORMATTER] Applying hierarchical formatting (unified={is_unified_request}")

        # Eliminar secciones de conclusión
        conclusion_patterns = [
            r'\b(en conclusión|en resumen|en definitiva|para finalizar|para terminar|en síntesis|en resumidas cuentas|en definitiva|por último|finalmente|a modo de cierre|a manera de conclusión|a modo de resumen|a modo de cierre|en resumidas cuentas|en líneas generales|en términos generales|en resumidas cuentas|en pocas palabras|en definitiva|en suma|en definitiva|en definitiva|en definitiva)\b[^.!?]*[.!?]',
            r'\b(como conclusión|como resumen|como cierre|como reflexión final|como síntesis)\b[^.!?]*[.!?]',
            r'\b(podemos concluir que|podemos resumir que|en resumen,|en conclusión,|finalmente,|por último,|para terminar,)\s*[^.!?]*[.!?]',
            r'\b(este documento|este texto|esta sección|este apartado|este trabajo|esta investigación|este análisis|este estudio|este informe|este reporte|este artículo|este ensayo|este documento|este escrito|este material|este recurso|este contenido)\s+\w+\s+(concluye|finaliza|termina|acaba|culmina|resume|sintetiza|cierra|recapitula|resalta|destaca|menciona|señala|indica|muestra|demuestra|evidencia|sugiere|propone|recomienda|sugiere|plantea|expone|presenta|describe|detalla|explica|analiza|examina|evalúa|valora|considera|reflexiona|discute|aborda|trata|desarrolla|profundiza|explora|investiga|estudia|analiza|examina|evalúa|valora|considera|reflexiona|discute|aborda|trata|desarrolla|profundiza|explora|investiga|estudia)[^.!?]*[.!?]'
        ]
        
        for pattern in conclusion_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Caso especial para recursos de profesor y alumnos
        if "para el profesor" in text.lower() and "para los alumnos" in text.lower():
            return self._format_teacher_student_resources(text)

        sections = self._extract_hierarchical_sections(text, is_unified_request)
        if not sections:
            return self._format_simple_list(text) if is_unified_request else text

        return "\n\n".join(sections)
        
    def _format_teacher_student_resources(self, text: str) -> str:
        """Formatea específicamente los recursos de profesor y alumnos"""
        # Extraer secciones
        prof_match = re.search(r'para el profesor[^:]*:(.*?)(?=para (?:los alumnos|el trabajo)|$)', text, re.IGNORECASE | re.DOTALL)
        alum_match = re.search(r'para (?:los alumnos|el alumno)[^:]*:(.*?)(?=para (?:el profesor|el trabajo)|$)', text, re.IGNORECASE | re.DOTALL)
        
        output = ["Los recursos didácticos mencionados son los siguientes:"]
        
        # Procesar recursos del profesor
        if prof_match:
            prof_items = [
                self._remove_trailing_connectors(i.strip()) 
                for i in prof_match.group(1).split(',') if i.strip()
            ]
            if prof_items:
                output.append(f"• **Para el profesor:** {', '.join(prof_items)}.")

        # Procesar recursos de los alumnos
        if alum_match:
            alum_items = [
                self._remove_trailing_connectors(i.strip()) 
                for i in alum_match.group(1).split(',') if i.strip()
            ]
            if alum_items:
                output.append(f"• **Para los alumnos:** {', '.join(alum_items)}.")

        
        return "\n".join(output)

    def _extract_hierarchical_sections(self, text: str, is_unified_request: bool = True) -> str:
        output = []
        if is_unified_request:
            output.append("Los recursos didácticos mencionados en el contexto son los siguientes:\n")

        section_titles = [
            "Para el profesor",
            "Para los alumnos",
            "Para el trabajo en el aula"
        ]

        sections = {}
        for i, title in enumerate(section_titles):
            pattern = rf"{title}.*?(?=(?:{'|'.join(section_titles[i+1:])}|$))"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[title] = match.group(0)

        blacklist = [
            r"\b(se menciona|se mencionan|se destacan|consisten en|estos recursos|esta información)\b",
            r"relacionados con el objeto.*",
            r"Por su parte, los recursos didácticos[.,]?\s*",
            r"\bY?\s*(?:[Aa]dem[aá]s|ADEMAS|Además)[.,]?\s*"
        ]

        def clean_item(item: str) -> str:
            # Remove blacklisted patterns
            for pat in blacklist:
                item = re.sub(pat, "", item, flags=re.IGNORECASE)
            
            # Remove last word if it's a variation of 'además'
            item = re.sub(r'\s+\b(?:[Aa]dem[aá]s|ADEMAS|Además)\b[.,]?\s*$', '', item.strip())
            
            return item.strip(" .:-")

        found_sections = []
        for title, content in sections.items():
            content = clean_item(content)

            # ✅ SOLO dividir si hay varias comas o punto y coma
            if content.count(",") >= 1 or ";" in content:
                raw_items = [c.strip() for c in re.split(r"[;,]", content)]
            else:
                raw_items = [content]

            items = [clean_item(i) for i in raw_items if len(clean_item(i)) > 2]
            if items:
                found_sections.append((title, items))

        if is_unified_request:
            # Formato de lista unificada
            if len(found_sections) > 1:
                for title, items in found_sections:
                    output.append(f"- **{title}:** {', '.join(items)}")
            elif len(found_sections) == 1:
                title, items = found_sections[0]
                bullets = "\n".join([f"  - {i}" for i in items])
                output.append(f"- **{title}:**\n{bullets}")
        else:
            # Formato de párrafo con comas
            for title, items in found_sections:
                output.append(f"**{title}:** {', '.join(items)}")
        return "\n".join(output)
        
         
    def _format_risks_benefits(self, text: str, is_unified_request: bool = True) -> str:
        """Formatea respuestas con secciones 'Riesgos:' y 'Beneficios:', limpia '**' sueltos y separa conclusiones."""
        # Intro previa a la primera sección
        first_sec = re.search(r'(?i)(riesgos?|beneficios?)\s*:', text)
        intro = text[:first_sec.start()].strip() if first_sec else ""
        intro = self._remove_stray_asterisks(intro)
    
        # Extraer bloques
        risks_match = re.search(r'(?is)riesgos?\s*:(.*?)(?=beneficios?\s*:|$)', text, re.IGNORECASE | re.DOTALL)
        ben_match = re.search(r'(?is)beneficios?\s*:(.*)$', text, re.IGNORECASE | re.DOTALL)
    
        def split_items(section_text: str) -> list:
            if not section_text:
                return []
            s = section_text.strip()
    
            # Si ya viene en viñetas por líneas
            bullets = []
            for line in s.splitlines():
                line = line.strip()
                if re.match(r'^[-•·*]\s+', line):
                    bullets.append(re.sub(r'^[-•·*]\s+', '', line).strip())
            if bullets:
                candidates = bullets
            else:
                # Dividir por oraciones o por ';'
                candidates = []
                parts = re.split(r'(?<=[.!?])\s+|;\s+', s)
                for part in parts:
                    part = part.strip(" •-*")
                    if not part:
                        continue
                    # Quitar encabezados repetidos
                    part = re.sub(r'^(?:[Rr]iesgos?:|[Bb]eneficios?:)\s*', '', part).strip()
                    # Limpiar asteriscos residuales (p. ej., 'palabra**:' -> 'palabra:')
                    part = re.sub(r'\*{1,3}([.,;:!?])', r'\1', part)
                    part = re.sub(r'^\*{1,3}', '', part)
                    part = re.sub(r'\*{1,3}$', '', part)
                    part = self._remove_stray_asterisks(part)
                    # Normalizar final
                    part = self._remove_trailing_connectors(part)
                    if part and not part.endswith(('.', '!', '?')):
                        part += '.'
                    # Evitar basura muy corta
                    if len(part) >= 4:
                        candidates.append(part)
    
            # Limpieza final (sin duplicados triviales)
            out = []
            seen = set()
            for c in candidates:
                c2 = re.sub(r'\s+', ' ', c).strip()
                if c2 and c2.lower() not in seen:
                    out.append(c2)
                    seen.add(c2.lower())
            return out
    
        risks = split_items(risks_match.group(1) if risks_match else "")
        benefits = split_items(ben_match.group(1) if ben_match else "")
    
        # Extraer posibles conclusiones que se colaron como viñetas
        def extract_conclusion(items: list) -> tuple[list, str]:
            conclusion_markers = (
                r'en conclusi[óo]n',
                r'en resumen',
                r'en s[ií]ntesis',
                r'en definitiva',
                r'para finalizar',
                r'finalmente',
                r'por [úu]ltimo',
                r'en suma',
                r'a modo de conclusi[óo]n',
            )
            if not items:
                return items, ""
            remain, concls = [], []
            for it in items:
                if re.match(rf'(?i)^\s*(?:{"|".join(conclusion_markers)})\b', it.strip()):
                    concls.append(it.rstrip())
                else:
                    remain.append(it)
            paragraph = " ".join(concls).strip()
            if paragraph and not paragraph.endswith(('.', '!', '?')):
                paragraph += '.'
            return remain, paragraph
    
        risks, concl_r = extract_conclusion(risks)
        benefits, concl_b = extract_conclusion(benefits)
        conclusion = " ".join([p for p in [concl_r, concl_b] if p]).strip()
    
        parts = []
        if intro:
            intro = intro.strip()
            if not intro.endswith(('.', '!', '?')):
                intro += '.'
            parts.append(intro)
    
        if is_unified_request:
            if risks:
                parts.append("**Riesgos:**")
                parts.extend([f"• {it}" for it in risks])
            if benefits:
                if risks:
                    parts.append("")  # separador
                parts.append("**Beneficios:**")
                parts.extend([f"• {it}" for it in benefits])
            if conclusion:
                parts.append("")  # separador
                parts.append(conclusion)
            return "\n\n".join([p for p in parts if p != ""])
        else:
            if risks:
                parts.append("**Riesgos:** " + " ".join(risks))
            if benefits:
                parts.append("**Beneficios:** " + " ".join(benefits))
            if conclusion:
                parts.append(conclusion)
            return "\n\n".join(parts)
         
    def _extract_items_for_section(self, content: str) -> list:
        """Extrae items específicamente para secciones jerárquicas"""
        if not content:
            return []
        
        items = []
        
        # Limpiar contenido de marcadores residuales
        content = re.sub(r'relacionados con el objeto de estudio.*', '', content, flags=re.IGNORECASE)
        content = content.strip()
        
        if not content:
            return []
        
        # Separar por guiones si los hay
        if ' - ' in content:
            raw_items = content.split(' - ')
        # Separar por comas si hay muchas
        elif content.count(',') >= 2:
            raw_items = content.split(',')
        # Si no hay separadores claros, dividir por conjunciones
        elif ' y ' in content:
            raw_items = re.split(r'\s+y\s+', content)
        else:
            # Contenido único
            raw_items = [content]
        
        for item in raw_items:
            item = item.strip()
            # Limpiar conectores y prefijos
            item = re.sub(r'^\s*[-•·*]\s*', '', item)
            item = re.sub(r'^\s*y\s+', '', item)
            item = re.sub(r'^\s*-\s*', '', item)
            item = item.strip()
            
            if item and len(item) > 2:
                # Capitalizar primera letra
                if item and item[0].islower():
                    item = item[0].upper() + item[1:]
                # Asegurar que no termine con punto múltiple
                item = re.sub(r'\.+$', '', item)
                if item.strip():
                    items.append(item.strip())
        
        return items

    def _format_simple_list(self, text: str) -> str:
        """Formatea como lista simple con viñetas y corta en cuanto empiece texto narrativo"""
        print("[FORMATTER] Applying simple list formatting")
        
        # Verificar si es una lista de recursos de profesor/alumnos
        if "para el profesor" in text.lower() and "para los alumnos" in text.lower():
            return self._format_teacher_student_resources(text)
            
        # Separar introducción de lista
        intro, list_part = self._separate_intro_and_list(text)
        
        # Extraer ítems candidatos a viñetas
        items = self._extract_items(list_part)
        
        # Particionar: viñetas vs. cola narrativa
        bullets, tail = self._split_bullets_and_tail(items)
        
        result_parts = []
        if intro:
            # Asegurar buen cierre de la introducción si viene sin puntuación
            if not intro.endswith(('.', '!', '?', ':')):
                intro += ':'
            result_parts.append(intro)
        
        if bullets:
            formatted_items = [f"• {item}" for item in bullets]
            result_parts.extend(formatted_items)
        
        # Si detectamos cola narrativa tras la lista, formatearla como párrafos
        if tail:
            narrative = self._format_narrative("\n".join(tail))
            result_parts.append(narrative)
        
        return '\n\n'.join(result_parts)

    def _format_mixed_content(self, text: str) -> str:
        """Formatea con una intro narrativa corta + lista de ideas principales"""
        print("[FORMATTER] Applying mixed content formatting")

        # Dividir en oraciones
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        if not sentences:
            return text

        # ✅ Intro: solo la primera oración
        intro = sentences[0]

        # El resto van a lista
        items = []
        for sentence in sentences[1:]:
            # Eliminar basura muy corta (palabras sueltas tipo "Donde Alberta")
            if len(sentence.split()) < 5:
                # Si es demasiado corta, unirla a la viñeta anterior
                if items:
                    items[-1] += " " + sentence
                else:
                    items.append(sentence)
                continue

    # Cortar frases largas si tienen demasiados conectores
            if "," in sentence and len(sentence.split()) > 25:
                subparts = [part.strip() for part in sentence.split(",") if len(part.split()) > 5]
                items.extend(subparts)
            else:
                items.append(sentence)


        # Construcción final
        result_parts = []
        result_parts.append(intro if intro.endswith('.') else intro + ".")
        if items:
            formatted_items = [f"• {self._remove_trailing_connectors(item)}" for item in items if item.strip()]
            result_parts.append("\n".join(formatted_items))

        return "\n\n".join(result_parts)


    def _format_narrative(self, text: str) -> str:
        """Formatea como texto narrativo, evitando listas y uniendo fragmentos sueltos"""
        print("[FORMATTER] Applying narrative formatting")

        # 1) Quitar posibles marcadores de lista al inicio de líneas
        text = re.sub(r'(?m)^\s*[-•·*]\s+', '', text)

        # 2) Preservar dobles saltos como separadores de párrafos
        #    y trabajar párrafo por párrafo para unir fragmentos internos
        raw_paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        cleaned_paragraphs = []

        connector_starts = (
            "que ", "lo que ", "sino ", "sin embargo ", "no obstante ", "funcionando ",
            "contrat", "así ", "de este modo ", "por lo tanto ", "por consiguiente ",
            "además ", "también ", "donde ", "cuando ", "mientras ", "aunque ",
        )

        for para in raw_paragraphs:
            # 2.a) Dividir en oraciones y fragmentos preservando separadores
            #     Cortamos por signos de cierre, pero mantenemos los caracteres finales.
            parts = re.split(r'(?<=[.!?])\s+|\n+', para)
            parts = [p.strip() for p in parts if p and p.strip()]

            merged = []
            for part in parts:
                lower = part.lower()

                # Unir con la oración previa si parece un conector o es demasiado corta
                if merged:
                    too_short = len(part.split()) <= 4
                    starts_with_connector = any(lower.startswith(c) for c in connector_starts)
                    # Si la parte anterior termina con dos puntos, seguir la misma oración
                    prev = merged[-1]
                    prev_ends_colon = prev.endswith(':')

                    if too_short or starts_with_connector or prev_ends_colon:
                        # Unir con espacio
                        merged[-1] = (prev.rstrip(' ')+ ' ' + part).strip()
                        continue

                merged.append(part)

            # 2.b) Asegurar puntuación final adecuada en cada oración del párrafo
            fixed_sentences = []
            for sent in merged:
                s = sent.strip()
                if not s:
                    continue
                if not s.endswith(('.', '!', '?')):
                    s += '.'
                fixed_sentences.append(s)

            # 2.c) Reunir párrafo final
            if fixed_sentences:
                cleaned_paragraphs.append(' '.join(fixed_sentences))

        return '\n\n'.join(cleaned_paragraphs)

    def _separate_intro_and_list(self, text: str) -> tuple:
        """Separa introducción de lista. Evita cortar por ':' genérico en texto narrativo."""
        # Patrones verbales que típicamente introducen una lista y requieren ':'
        list_introducers = [
            r'(?:incluye|incluyen)\s*:',
            r'(?:son)\s*:',
            r'(?:menciona|mencionan)\s*:',
            r'(?:enumera|enumeran)\s*:',
            r'(?:contiene|contienen)\s*:',
            r'(?:presenta|presentan)\s*:',
        ]
        for pattern in list_introducers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                split_point = match.end()
                intro = text[:split_point].strip()
                list_part = text[split_point:].strip()
                return intro, list_part
        # Si no hay intro clara de lista, devolver todo como narrativo
        return "", text

    def _extract_items(self, content: str) -> list:
        """Extrae items individuales del contenido"""
        if not content:
            return []
        
        items = []
        
        # Limpiar contenido de marcadores de sección que se colaron
        section_markers = ['Para el profesor:', 'Para el alumno:', 'Para los alumnos:', 'Para el trabajo en el aula:']
        for marker in section_markers:
            content = re.sub(re.escape(marker), '', content, flags=re.IGNORECASE)
        
        content = content.strip()
        if not content:
            return []
        
        # ✅ Paso extra: dividir enumeraciones que vienen corridas en una sola línea
        if re.search(r'\d+[.)]\s+', content):
            # Si todo viene junto, separar en ítems usando regex global
            parts = re.split(r'\s*\d+[.)]\s*', content)
            items = [p.strip() for p in parts if p.strip()]
        
        # Si ya tiene viñetas con - • *
        elif re.search(r'^\s*[-•·*]\s+', content, re.MULTILINE):
            for line in content.split('\n'):
                line = line.strip()
                if re.match(r'^[-•·*]\s+', line):
                    item = re.sub(r'^[-•·*]\s+', '', line).strip()
                    if item:
                        for marker in section_markers:
                            item = re.sub(re.escape(marker), '', item, flags=re.IGNORECASE)
                        item = item.strip()
                        if item and len(item) > 2:
                            items.append(item)
        
        # Si tiene números pero en líneas separadas
        elif re.search(r'^\s*\d+[.)]\s+', content, re.MULTILINE):
            for line in content.split('\n'):
                line = line.strip()
                if re.match(r'^\d+[.)]\s+', line):
                    item = re.sub(r'^\d+[.)]\s+', '', line).strip()
                    if item:
                        for marker in section_markers:
                            item = re.sub(re.escape(marker), '', item, flags=re.IGNORECASE)
                        item = item.strip()
                        if item and len(item) > 2:
                            items.append(item)
        
        # Si tiene comas o guiones como separadores
        elif ',' in content or ' - ' in content:
            if ',' in content:
                raw_items = content.split(',')
            else:
                raw_items = content.split(' - ')
            
            for item in raw_items:
                item = item.strip()
                item = re.sub(r'\s*y\s*$', '', item)
                item = re.sub(r'^\s*y\s*', '', item)
                item = re.sub(r'^\s*-\s*', '', item)
                
                for marker in section_markers:
                    item = re.sub(re.escape(marker), '', item, flags=re.IGNORECASE)
                
                item = item.strip()
                if item and len(item) > 2:
                    items.append(item)
        
        # Contenido único (sin separadores claros)
        elif len(content.strip()) > 3:
            clean_content = content
            for marker in section_markers:
                clean_content = re.sub(re.escape(marker), '', clean_content, flags=re.IGNORECASE)
            
            clean_content = clean_content.strip()
            if clean_content and len(clean_content) > 3:
                items.append(clean_content)
        
        # Limpiar y normalizar items finales
        cleaned_items = []
        for item in items:
            item = item.strip()
            if item and len(item) > 1:
                item = re.sub(r'\.+$', '', item)
                if item and item[0].islower():
                    item = item[0].upper() + item[1:]
                if item.strip():
                    cleaned_items.append(item.strip())
        
        return cleaned_items

    def _split_bullets_and_tail(self, items: list) -> tuple:
        """Divide ítems en:
        - bullets: elementos cortos/nominales apropiados para viñetas
        - tail: oraciones largas que deben mostrarse como párrafos (cola narrativa)
        Heurísticas:
        - Inicia cola si un ítem tiene >= 14 palabras
        - O si empieza con marcadores discursivos típicos de cierre/desarrollo
        """
        bullets = []
        tail = []
        started_tail = False
        tail_markers = (
            "En esencia", "En resumen", "En conclusión", "Finalmente", "Por último",
            "El viaje", "Un progreso", "Una búsqueda", "Este viaje", "Puede ser", "Se presenta"
        )

        for item in items:
            text = item.strip()
            wc = len(text.split())
            is_marker = any(text.startswith(m) for m in tail_markers)
            if started_tail or wc >= 14 or is_marker:
                started_tail = True
                tail.append(text)
            else:
                bullets.append(text)
        return bullets, tail

    
    def _remove_trailing_connectors(self, text: str) -> str:
        """Elimina conectores residuales como 'además', 'por último', etc."""
        trailing_patterns = [
            r'\s*\badem[aá]s\b[.,;:]*$',
            r'\s*\bpor último\b[.,;:]*$',
            r'\s*\bfinalmente\b[.,;:]*$',
            r'\s*\ben conclusión\b[.,;:]*$',
            r'\s*\ben resumen\b[.,;:]*$',
            r'\s*\bpara terminar\b[.,;:]*$'
        ]
        for pat in trailing_patterns:
            text = re.sub(pat, '', text, flags=re.IGNORECASE)
        return text.strip(" .,:;")
    def _remove_stray_asterisks(self, text: str) -> str:
        """Elimina asteriscos sueltos/artefactos sin romper encabezados en negrita que sí queremos mantener.
        Preserva específicamente: **Riesgos:**, **Beneficios:**, **Para el profesor:**, **Para los alumnos:**"""
        if not text:
            return text

        # 1) Proteger encabezados válidos reemplazando temporalmente los ** por marcadores
        protect_map = {
            r"\*\*\s*Riesgos\s*:\s*\*\*": "§§BOLD_RIESGOS§§",
            r"\*\*\s*Beneficios\s*:\s*\*\*": "§§BOLD_BENEFICIOS§§",
            r"\*\*\s*Para el profesor\s*:\s*\*\*": "§§BOLD_PROF§§",
            r"\*\*\s*Para los alumnos\s*:\s*\*\*": "§§BOLD_ALUM§§",
        }
        for pat, token in protect_map.items():
            text = re.sub(pat, token, text, flags=re.IGNORECASE)

        # 2) Eliminar líneas compuestas solo por asteriscos (y posible .,:;!?)
        text = re.sub(r'(?m)^\s*\*{1,3}\s*[.,;:!?]?\s*$', '', text)

        # 3) Quitar asteriscos pegados a signos de puntuación: "palabra**:" -> "palabra:"
        text = re.sub(r'\*{1,3}([.,;:!?])', r'\1', text)

        # 4) Quitar dobles asteriscos no balanceados (p. ej., "**Sr. Chinarro")
        #    Regla: si aparece ** y no hay otro ** de cierre razonablemente cerca, lo eliminamos.
        #    Simplificación segura: eliminar cualquier ** que no forme parte de nuestros encabezados protegidos.
        text = re.sub(r'\*\*(?!\S)', '', text)     # "** " al final de token
        text = re.sub(r'(?<!\S)\*\*', '', text)    # "**" al inicio de línea/frase
        # Y como medida extra, eliminar cualquier '**' restante que no esté protegido
        text = text.replace("**", "")

        # 5) Quitar asteriscos simples sueltos que no sean parte de **negrita**
        text = re.sub(r'(?<!\*)\*(?!\*)', '', text)

        # 6) Restaurar encabezados protegidos
        restore_map = {
            "§§BOLD_RIESGOS§§": "**Riesgos:**",
            "§§BOLD_BENEFICIOS§§": "**Beneficios:**",
            "§§BOLD_PROF§§": "**Para el profesor:**",
            "§§BOLD_ALUM§§": "**Para los alumnos:**",
        }
        for token, val in restore_map.items():
            text = text.replace(token, val)

        # 7) Normalizar espacios
        text = re.sub(r'[ \t]+', ' ', text).strip()
        return text

    

    def _sentence_contains_list(self, sentence: str) -> bool:
        """Detecta si una oración contiene una lista"""
        list_signals = [
            r'incluye[n]?:',
            r'son:',
            r'como:',
            r'tales como',
            r'entre otros'
        ]
        if any(re.search(signal, sentence, re.IGNORECASE) for signal in list_signals):
            return True
        # También tratamos oraciones cortas separadas como viñetas
        return sentence.count(',') >= 2 or len(sentence.split()) <= 12

    def _final_cleanup(self, text: str) -> str:
        """Limpieza final del resultado"""
        # Normalizar saltos de línea múltiples a doble salto (párrafos)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # Colapsar espacios múltiples
        text = re.sub(r'[ \t]+', ' ', text)

        # Eliminar líneas que son solo asteriscos o asteriscos con puntuación (artefactos)
        text = re.sub(r'(?m)^\s*\*{1,3}\s*[.,;:!?]?\s*$', '', text)
        # Limpieza de asteriscos sueltos dentro de oraciones (sin afectar **negrita** válida)
        text = self._remove_stray_asterisks(text)

        # Si NO es una lista (no hay viñetas al inicio de línea), convertir saltos simples a espacios
        if not re.search(r'(?m)^\s*[•\-*]\s+', text):
            # Reemplazar saltos simples por espacios, preservando párrafos
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

        text = text.strip()

        # Asegurar que la respuesta termine con puntuación adecuada
        if text and not re.search(r'[.!?]\s*$', text):
            text += '.'

        return text
