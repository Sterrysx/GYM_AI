#!/usr/bin/env python3
"""
Generate front + back anatomical body SVGs with clickable muscle-group regions.
CLEAN version — no <text> labels. Pure abstract cyberpunk shapes.
Output: frontend/public/body_front.svg  &  frontend/public/body_back.svg
"""
import textwrap, pathlib

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "public"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FRONT_SVG = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 600" width="300" height="600">
  <style>
    .body-outline { fill: none; stroke: #333; stroke-width: 1; }
    .muscle-region { fill: rgba(50,50,50,0.2); stroke: #444; stroke-width: 0.6; cursor: pointer; transition: all 0.3s ease-in-out; }
  </style>
  <ellipse class="body-outline" cx="150" cy="42" rx="28" ry="34" />
  <rect class="body-outline" x="140" y="74" width="20" height="16" rx="4" />
  <path class="body-outline" d="M108,90 Q100,100 96,130 L92,200 Q90,230 100,260 L108,280 Q130,290 150,292 Q170,290 192,280 L200,260 Q210,230 208,200 L204,130 Q200,100 192,90 Z" />
  <path class="body-outline" d="M96,95 Q78,100 65,130 L55,170 Q48,190 52,210 L60,240 Q64,250 68,245 L75,220 Q80,200 78,180 L85,150 Q90,130 96,120" />
  <path class="body-outline" d="M204,95 Q222,100 235,130 L245,170 Q252,190 248,210 L240,240 Q236,250 232,245 L225,220 Q220,200 222,180 L215,150 Q210,130 204,120" />
  <path class="body-outline" d="M108,280 Q105,310 102,360 L98,420 Q96,460 98,500 L102,540 Q104,560 100,580 L96,595 L120,595 L118,580 Q116,560 118,540 L125,460 Q128,420 130,380 L135,330 Q138,300 140,292" />
  <path class="body-outline" d="M192,280 Q195,310 198,360 L202,420 Q204,460 202,500 L198,540 Q196,560 200,580 L204,595 L180,595 L182,580 Q184,560 182,540 L175,460 Q172,420 170,380 L165,330 Q162,300 160,292" />
  <path id="chest" class="muscle-region" data-muscle="chest" d="M118,100 Q125,95 150,98 Q175,95 182,100 L186,115 Q180,135 150,140 Q120,135 114,115 Z" />
  <path id="shoulders-l" class="muscle-region" data-muscle="shoulders" d="M96,92 Q88,95 82,108 L86,128 Q92,118 108,100 Z" />
  <path id="shoulders-r" class="muscle-region" data-muscle="shoulders" d="M204,92 Q212,95 218,108 L214,128 Q208,118 192,100 Z" />
  <path id="abs" class="muscle-region" data-muscle="abs" d="M130,142 Q130,155 128,180 L126,210 Q125,240 128,265 Q138,275 150,278 Q162,275 172,265 Q175,240 174,210 L172,180 Q170,155 170,142 Q160,148 150,148 Q140,148 130,142 Z" />
  <line class="body-outline" x1="150" y1="148" x2="150" y2="275" stroke="#333" stroke-width="0.4" opacity="0.3"/>
  <line class="body-outline" x1="132" y1="165" x2="168" y2="165" stroke="#333" stroke-width="0.3" opacity="0.25"/>
  <line class="body-outline" x1="130" y1="190" x2="170" y2="190" stroke="#333" stroke-width="0.3" opacity="0.25"/>
  <line class="body-outline" x1="129" y1="215" x2="171" y2="215" stroke="#333" stroke-width="0.3" opacity="0.25"/>
  <line class="body-outline" x1="128" y1="240" x2="172" y2="240" stroke="#333" stroke-width="0.3" opacity="0.25"/>
  <path id="biceps-l" class="muscle-region" data-muscle="biceps" d="M78,135 Q72,150 68,170 L65,190 Q70,192 80,185 L85,160 Q86,145 84,135 Z" />
  <path id="biceps-r" class="muscle-region" data-muscle="biceps" d="M222,135 Q228,150 232,170 L235,190 Q230,192 220,185 L215,160 Q214,145 216,135 Z" />
  <path id="forearms-l" class="muscle-region" data-muscle="forearms" d="M65,192 Q60,210 58,225 L62,240 Q66,238 72,225 L78,205 Q80,195 78,188 Z" />
  <path id="forearms-r" class="muscle-region" data-muscle="forearms" d="M235,192 Q240,210 242,225 L238,240 Q234,238 228,225 L222,205 Q220,195 222,188 Z" />
  <path id="triceps-l" class="muscle-region" data-muscle="triceps" d="M88,120 Q84,130 80,145 L78,160 Q82,158 88,145 L92,130 Z" />
  <path id="triceps-r" class="muscle-region" data-muscle="triceps" d="M212,120 Q216,130 220,145 L222,160 Q218,158 212,145 L208,130 Z" />
  <path id="quads-l" class="muscle-region" data-muscle="quads" d="M112,282 Q108,310 105,350 L102,390 Q100,420 104,440 Q112,445 120,440 L128,400 Q132,370 134,340 L136,310 Q138,295 138,290 Q128,288 118,285 Z" />
  <path id="quads-r" class="muscle-region" data-muscle="quads" d="M188,282 Q192,310 195,350 L198,390 Q200,420 196,440 Q188,445 180,440 L172,400 Q168,370 166,340 L164,310 Q162,295 162,290 Q172,288 182,285 Z" />
  <path id="calves-l" class="muscle-region" data-muscle="calves" d="M104,455 Q100,480 100,510 L102,540 Q106,545 112,540 L118,510 Q120,480 118,455 Q112,450 104,455 Z" />
  <path id="calves-r" class="muscle-region" data-muscle="calves" d="M196,455 Q200,480 200,510 L198,540 Q194,545 188,540 L182,510 Q180,480 182,455 Q188,450 196,455 Z" />
</svg>
""")

BACK_SVG = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 600" width="300" height="600">
  <style>
    .body-outline { fill: none; stroke: #333; stroke-width: 1; }
    .muscle-region { fill: rgba(50,50,50,0.2); stroke: #444; stroke-width: 0.6; cursor: pointer; transition: all 0.3s ease-in-out; }
  </style>
  <ellipse class="body-outline" cx="150" cy="42" rx="28" ry="34" />
  <rect class="body-outline" x="140" y="74" width="20" height="16" rx="4" />
  <path class="body-outline" d="M108,90 Q100,100 96,130 L92,200 Q90,230 100,260 L108,280 Q130,290 150,292 Q170,290 192,280 L200,260 Q210,230 208,200 L204,130 Q200,100 192,90 Z" />
  <path class="body-outline" d="M96,95 Q78,100 65,130 L55,170 Q48,190 52,210 L60,240 Q64,250 68,245 L75,220 Q80,200 78,180 L85,150 Q90,130 96,120" />
  <path class="body-outline" d="M204,95 Q222,100 235,130 L245,170 Q252,190 248,210 L240,240 Q236,250 232,245 L225,220 Q220,200 222,180 L215,150 Q210,130 204,120" />
  <path class="body-outline" d="M108,280 Q105,310 102,360 L98,420 Q96,460 98,500 L102,540 Q104,560 100,580 L96,595 L120,595 L118,580 Q116,560 118,540 L125,460 Q128,420 130,380 L135,330 Q138,300 140,292" />
  <path class="body-outline" d="M192,280 Q195,310 198,360 L202,420 Q204,460 202,500 L198,540 Q196,560 200,580 L204,595 L180,595 L182,580 Q184,560 182,540 L175,460 Q172,420 170,380 L165,330 Q162,300 160,292" />
  <path id="traps" class="muscle-region" data-muscle="traps" d="M130,82 Q140,80 150,80 Q160,80 170,82 L185,92 Q170,88 150,90 Q130,88 115,92 Z" />
  <path id="rear_delts-l" class="muscle-region" data-muscle="rear_delts" d="M96,92 Q88,95 82,108 L86,128 Q92,118 108,100 Z" />
  <path id="rear_delts-r" class="muscle-region" data-muscle="rear_delts" d="M204,92 Q212,95 218,108 L214,128 Q208,118 192,100 Z" />
  <path id="back-upper" class="muscle-region" data-muscle="back" d="M115,95 Q130,92 150,93 Q170,92 185,95 L188,120 Q180,130 150,132 Q120,130 112,120 Z" />
  <path id="back-lat-l" class="muscle-region" data-muscle="back" d="M112,122 Q108,140 104,165 L100,195 Q98,210 100,230 L108,245 Q120,248 130,242 L135,210 Q136,180 135,155 L130,132 Q120,130 112,122 Z" />
  <path id="back-lat-r" class="muscle-region" data-muscle="back" d="M188,122 Q192,140 196,165 L200,195 Q202,210 200,230 L192,245 Q180,248 170,242 L165,210 Q164,180 165,155 L170,132 Q180,130 188,122 Z" />
  <path id="lower_back" class="muscle-region" data-muscle="lower_back" d="M130,243 Q140,250 150,252 Q160,250 170,243 L174,265 Q162,278 150,280 Q138,278 126,265 Z" />
  <path id="triceps-bl" class="muscle-region" data-muscle="triceps" d="M86,118 Q80,135 75,155 L72,175 Q76,178 82,170 L88,150 Q92,135 94,120 Z" />
  <path id="triceps-br" class="muscle-region" data-muscle="triceps" d="M214,118 Q220,135 225,155 L228,175 Q224,178 218,170 L212,150 Q208,135 206,120 Z" />
  <path id="glutes" class="muscle-region" data-muscle="glutes" d="M112,268 Q120,285 150,288 Q180,285 188,268 L192,280 Q182,298 150,300 Q118,298 108,280 Z" />
  <path id="hamstrings-l" class="muscle-region" data-muscle="hamstrings" d="M110,296 Q107,325 105,355 L102,395 Q100,420 104,440 Q112,445 120,440 L126,400 Q130,370 132,340 L134,310 Q135,300 134,296 Q122,298 110,296 Z" />
  <path id="hamstrings-r" class="muscle-region" data-muscle="hamstrings" d="M190,296 Q193,325 195,355 L198,395 Q200,420 196,440 Q188,445 180,440 L174,400 Q170,370 168,340 L166,310 Q165,300 166,296 Q178,298 190,296 Z" />
  <path id="calves-bl" class="muscle-region" data-muscle="calves" d="M104,445 Q98,468 98,495 L100,530 Q105,540 112,535 L118,495 Q120,468 118,445 Q112,442 104,445 Z" />
  <path id="calves-br" class="muscle-region" data-muscle="calves" d="M196,445 Q202,468 202,495 L200,530 Q195,540 188,535 L182,495 Q180,468 182,445 Q188,442 196,445 Z" />
</svg>
""")

def main():
    (OUT_DIR / "body_front.svg").write_text(FRONT_SVG)
    (OUT_DIR / "body_back.svg").write_text(BACK_SVG)
    print("✓ Generated clean SVGs (no text labels)")

if __name__ == "__main__":
    main()
