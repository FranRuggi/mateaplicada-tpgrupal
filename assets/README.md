# Personajes de la escena arcade

`personajes-arcade.png` es una hoja con fondo transparente y tres celdas iguales:
Alice a la izquierda, Eve al centro y Bob a la derecha. La interfaz la carga con
Tk, recorta cada celda y la reduce conservando los píxeles. No requiere Pillow,
Blender, Internet ni claves de API al ejecutar la aplicación.

Recursos generados con la herramienta integrada ImageGen el 29/10/2026 y elegidos
durante la propuesta visual. La versión final mantiene a Alice y Bob y cambia la
expresión de Eve por la de una villana, según lo pedido.

Prompt de generación:

> Use case: stylized-concept. Asset type: transparent character sprite sheet for an educational 2D arcade game about Diffie-Hellman. Create exactly THREE full-body pixel-art characters arranged in ONE horizontal row on a genuinely transparent background. Canvas ratio exactly 3:1, split into three equal square cells; each character centered in its own cell, no overlap, generous transparent margin. Left cell: Alice, young adult woman with dark shoulder-length hair, bright blue jacket, navy pants, sneakers, facing right, friendly determined expression, arms in a relaxed ready-to-send pose. Middle cell: Eve, woman spy with dark purple fedora and trenchcoat, coral scarf, binoculars held in hands, facing front slightly left, playful sneaky expression. Right cell: Bob, young adult man with curly brown hair, mint green jacket, dark pants and sneakers, facing left, friendly determined expression. Style: polished 16-bit arcade adventure sprites, crisp square pixel clusters, limited color palette, dark outlines, expressive faces, 3-head-tall proportions, consistent scale and feet baseline, standing poses suitable for basic walking/hopping animation. Clearly pixel art, no smooth vector edges, no soft 3D shading. Transparent background ONLY. No scenery, floor, shadows outside the sprites, desks, laptops, game UI, labels, letters, numbers, icons, or watermark. All three figures fully inside their cells, entire head, feet and hands visible.

Prompt del ajuste final:

> Edit ONLY the middle character Eve. Keep Alice on the left and Bob on the right exactly unchanged. Preserve the three equal-width sprite cells, full-body scale, standing pose, common feet baseline, crisp 16-bit pixel art, and genuine transparent alpha background. Eve must look like a recognizable arcade VILLAIN, not a friendly protagonist: sharply angled raised dark eyebrows, narrowed mischievous eyes looking sideways toward Alice, a prominent crooked evil grin/smirk with teeth, a slight menacing shadow under the purple fedora brim. Make her facial expression exaggerated and readable at small sprite size. Keep her human, not monster. Keep her dark purple spy trenchcoat, coral red scarf, purple boots and binoculars in hands BELOW her face so the face stays unobscured. Slightly hunched conspiratorial body language is okay, still centered in the same middle cell. Playful cartoon villain appropriate for a university educational game. No new objects or characters, no text, no background, no frame or UI. Alice and Bob must remain exactly as they are.

Para distribuir un ejecutable también se debe incluir esta carpeta `assets`.
