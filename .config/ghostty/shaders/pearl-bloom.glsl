// Pearl Bloom — a compact, inside-first Rosé Pine block-cursor glow.
// Target: Ghostty 1.3.1 custom-shader interface.

const float PB_PI = 3.14159265358979323846;
const float PB_TAU = 6.28318530717958647692;

// Canonical Rosé Pine colors, precomputed as OKLCH (L, C, hue radians).
const vec3 PB_PEARL     = vec3(0.9870301, 0.0106882, 1.3369286); // #fffaf3
const vec3 PB_GOLD      = vec3(0.8429022, 0.1100442, 1.3020481); // #f6c177
const vec3 PB_ROSE      = vec3(0.8362735, 0.0544100, 0.3689812); // #ebbcba
const vec3 PB_FOAM      = vec3(0.8219128, 0.0543299, 3.6574914); // #9ccfd8
const vec3 PB_DAWN_GOLD = vec3(0.7554863, 0.1459300, 1.2172499); // #ea9d34
const vec3 PB_DAWN_ROSE = vec3(0.6957348, 0.1057738, 0.4019985); // #d7827e
const vec3 PB_DAWN_FOAM = vec3(0.6289005, 0.0660668, 3.6673344); // #56949f
const vec3 PB_GLYPH     = vec3(0.2133550, 0.0254658, 5.0811948); // #191724

const float PB_FLOW_RATE = 1.05;

// One calm inhale and exhale takes about ten seconds. The block geometry
// never changes: only its light and the compact bloom around it breathe.
const float PB_BREATH_RATE = 0.62;
const float PB_CORE_BREATH_LIGHTNESS = 0.024;
const float PB_CORE_BREATH_CHROMA = 0.12;
const float PB_BLOOM_BREATH_REACH = 0.16;
const float PB_BLOOM_BREATH_STRENGTH = 0.10;

float pbSdBox(vec2 point, vec2 halfSize) {
    vec2 delta = abs(point) - halfSize;
    return length(max(delta, 0.0)) + min(max(delta.x, delta.y), 0.0);
}

float pbHash(float value) {
    value = fract(value * 0.1031);
    value *= value + 33.33;
    value *= value + value;
    return fract(value);
}

float pbNoise(float value) {
    float cell = floor(value);
    float offset = fract(value);
    float eased = offset * offset * offset
        * (offset * (offset * 6.0 - 15.0) + 10.0);
    return mix(pbHash(cell), pbHash(cell + 1.0), eased);
}

float pbFbm(float value) {
    // Three unrolled octaves: organic enough for a cursor, with no loop cost.
    return pbNoise(value) * 0.5714
        + pbNoise(value * 2.03 + 17.17) * 0.2857
        + pbNoise(value * 4.11 + 43.71) * 0.1429;
}

float pbQuintic(float value) {
    return value * value * value
        * (value * (value * 6.0 - 15.0) + 10.0);
}

float pbBreath(float time) {
    // A slightly noisy phase avoids metronomic repetition. Inhale occupies
    // 38% of the cycle; exhale gets the longer, calmer 62%.
    float phaseWarp = (pbFbm(time * 0.055 + 81.0) - 0.5) * 0.075;
    float phase = fract(time * PB_BREATH_RATE / PB_TAU + phaseWarp);
    float envelope = phase < 0.38
        ? phase / 0.38
        : 1.0 - (phase - 0.38) / 0.62;
    return pbQuintic(clamp(envelope, 0.0, 1.0));
}

vec3 pbMixOklch(vec3 from, vec3 to, float amount) {
    float hueDelta = mod(to.z - from.z + PB_PI, PB_TAU) - PB_PI;
    return vec3(mix(from.xy, to.xy, amount), from.z + hueDelta * amount);
}

vec3 pbOklabToLinearSrgb(vec3 lab) {
    float l = lab.x + 0.3963377774 * lab.y + 0.2158037573 * lab.z;
    float m = lab.x - 0.1055613458 * lab.y - 0.0638541728 * lab.z;
    float s = lab.x - 0.0894841775 * lab.y - 1.2914855480 * lab.z;

    l = l * l * l;
    m = m * m * m;
    s = s * s * s;

    return vec3(
         4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    );
}

vec3 pbOklchToOklab(vec3 lch) {
    return vec3(lch.x, lch.y * cos(lch.z), lch.y * sin(lch.z));
}

vec3 pbLinearToSrgb(vec3 linearColor) {
    vec3 low = 12.92 * linearColor;
    vec3 high = 1.055 * pow(max(linearColor, vec3(0.0)), vec3(1.0 / 2.4)) - 0.055;
    return clamp(mix(low, high, step(vec3(0.0031308), linearColor)), 0.0, 1.0);
}

vec3 pbOklchToSrgb(vec3 lch) {
    return pbLinearToSrgb(pbOklabToLinearSrgb(pbOklchToOklab(lch)));
}

vec3 pbOklabToSrgb(vec3 lab) {
    return pbLinearToSrgb(pbOklabToLinearSrgb(lab));
}

vec3 pbPalette(float position, float dawnAmount) {
    vec3 gold = mix(PB_GOLD, PB_DAWN_GOLD, dawnAmount);
    vec3 rose = mix(PB_ROSE, PB_DAWN_ROSE, dawnAmount);
    vec3 foam = mix(PB_FOAM, PB_DAWN_FOAM, dawnAmount);
    float t = clamp(position, 0.0, 1.0);

    if (t < 0.30) {
        return pbMixOklch(PB_PEARL, gold, smoothstep(0.0, 0.30, t));
    }
    if (t < 0.68) {
        return pbMixOklch(gold, rose, smoothstep(0.30, 0.68, t));
    }
    return pbMixOklch(rose, foam, smoothstep(0.68, 1.0, t));
}

float pbLuminance(vec3 color) {
    return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec4 terminal = texture(iChannel0, fragCoord / iResolution.xy);
    fragColor = terminal;

    if (iCursorVisible == 0 || iCurrentCursorStyle != CURSORSTYLE_BLOCK) {
        return;
    }
    if (iCurrentCursor.z <= 0.0 || iCurrentCursor.w <= 0.0) {
        return;
    }

    vec2 halfSize = max(iCurrentCursor.zw * 0.5, vec2(1.0));
    vec2 center = vec2(
        iCurrentCursor.x + halfSize.x,
        iCurrentCursor.y - halfSize.y
    );
    vec2 fromCenter = fragCoord - center;
    vec2 local = fromCenter / halfSize;
    float distanceToBlock = pbSdBox(fromCenter, halfSize);
    float baseBloomRadius = max(min(iCurrentCursor.z, iCurrentCursor.w) * 0.55, 1.0);
    float maximumBloomRadius = baseBloomRadius
        * (1.0 + 0.5 * PB_BLOOM_BREATH_REACH);
    if (distanceToBlock > maximumBloomRadius * 2.48) {
        return;
    }

    float breath = pbBreath(iTime);
    float bloomRadius = baseBloomRadius
        * (1.0 + (breath - 0.5) * PB_BLOOM_BREATH_REACH);
    float edgeWidth = max(fwidth(distanceToBlock), 0.75);
    float inside = 1.0 - smoothstep(-edgeWidth, edgeWidth, distanceToBlock);

    // Dawn anchors are darker and more chromatic so Pearl remains legible on
    // a light terminal; the transition stays continuous for custom themes.
    float dawnAmount = smoothstep(0.55, 0.78, pbLuminance(iBackgroundColor));

    // Oversized color masses meander beyond the block's bounds. Only their
    // broad liquid boundaries pass through the cursor—never discrete bubbles.
    float flowTime = iTime * PB_FLOW_RATE;
    vec2 goldCenter = vec2(
        mix(-0.62, 0.54, pbFbm(flowTime * 0.72 + 2.1)),
        mix(0.88, -0.92, pbFbm(flowTime * 0.55 + 9.7))
    );
    vec2 roseCenter = vec2(
        mix(0.68, -0.58, pbFbm(flowTime * 0.61 + 23.4)),
        mix(-0.86, 0.90, pbFbm(flowTime * 0.47 + 31.8))
    );
    vec2 foamCenter = vec2(
        mix(-0.52, 0.62, pbFbm(flowTime * 0.83 + 47.2)),
        mix(0.96, -0.72, pbFbm(flowTime * 0.69 + 58.6))
    );

    vec2 goldPoint = (local - goldCenter) * vec2(0.48, 0.62);
    vec2 rosePoint = (local - roseCenter) * vec2(0.54, 0.68);
    vec2 foamPoint = (local - foamCenter) * vec2(0.62, 0.82);
    float goldLobe = exp(-1.22 * dot(goldPoint, goldPoint));
    float roseLobe = exp(-1.38 * dot(rosePoint, rosePoint));
    float foamLobe = exp(-1.64 * dot(foamPoint, foamPoint));
    float organicField = pbFbm(
        flowTime * 0.88 + local.x * 0.38 - local.y * 0.29 + 71.3
    );

    vec3 gold = mix(PB_GOLD, PB_DAWN_GOLD, dawnAmount);
    vec3 rose = mix(PB_ROSE, PB_DAWN_ROSE, dawnAmount);
    vec3 foam = mix(PB_FOAM, PB_DAWN_FOAM, dawnAmount);
    float pearlSource = clamp(
        goldLobe * 0.44 + roseLobe * 0.32 + organicField * 0.18,
        0.0,
        1.0
    );
    float goldWeight = 0.28 + goldLobe * 0.92 + organicField * 0.08;
    float roseWeight = 0.34 + roseLobe * 0.84;
    float foamWeight = 0.12 + foamLobe * 0.50;
    float pearlWeight = (0.12 + pearlSource * 0.54) * mix(0.88, 1.12, breath);
    float totalWeight = goldWeight + roseWeight + foamWeight + pearlWeight;
    vec3 fieldOklab = (
        pbOklchToOklab(gold) * goldWeight
        + pbOklchToOklab(rose) * roseWeight
        + pbOklchToOklab(foam) * foamWeight
        + pbOklchToOklab(PB_PEARL) * pearlWeight
    ) / totalWeight;
    float fluidRelief = (goldLobe - roseLobe) * 0.50
        + (foamLobe - 0.64) * 0.30
        + (organicField - 0.50) * 0.36;
    fieldOklab.x = clamp(
        fieldOklab.x
            + (breath - 0.5) * PB_CORE_BREATH_LIGHTNESS
            + fluidRelief * mix(0.028, 0.055, dawnAmount),
        0.0,
        1.0
    );
    fieldOklab.yz *= 1.0
        + (breath - 0.5) * PB_CORE_BREATH_CHROMA
        + mix(0.18, 0.32, dawnAmount)
        + fluidRelief * 0.12;
    vec3 fieldColor = pbOklabToSrgb(fieldOklab);

    // The rendered cursor fill is uniform. Pixels sufficiently different
    // from it are the cursor glyph and are recolored to Rosé Pine base so the
    // character remains readable over the luminous field.
    float glyphDifference = distance(terminal.rgb, iCurrentCursorColor.rgb);
    float glyphMask = smoothstep(0.055, 0.18, glyphDifference);
    vec3 glyphColor = pbOklchToSrgb(PB_GLYPH);
    vec3 coreColor = mix(fieldColor, glyphColor, glyphMask);

    // Keep the spill smaller and dimmer than the emitter. The explicit support
    // cutoff prevents an imperceptible Gaussian tail from touching the screen.
    float outsideDistance = max(distanceToBlock, 0.0);
    float haloNoise = pbFbm(
        flowTime * 0.76 + local.x * 0.37 + local.y * 0.53 + 93.7
    );
    float haloLobe = mix(0.82, 1.22, haloNoise)
        + goldLobe * 0.10
        + foamLobe * 0.05;
    float haloRadius = bloomRadius * haloLobe;
    float bloomSupport = 1.0 - smoothstep(
        haloRadius * 1.28,
        haloRadius * 2.15,
        outsideDistance
    );
    float bloom = exp(-pow(outsideDistance / haloRadius, 2.0))
        * bloomSupport
        * (1.0 - inside)
        * (0.24 + (breath - 0.5) * PB_BLOOM_BREATH_STRENGTH);
    vec3 bloomOklab = mix(fieldOklab, pbOklchToOklab(PB_PEARL), 0.16);
    bloomOklab.x -= dawnAmount * 0.045;
    bloomOklab.yz *= 1.0 + dawnAmount * 0.42;
    vec3 bloomColor = pbOklabToSrgb(bloomOklab);
    vec3 screenBloom = 1.0 - (1.0 - terminal.rgb) * (1.0 - bloomColor * bloom);
    vec3 tintBloom = mix(terminal.rgb, bloomColor, bloom * 0.95);
    vec3 withBloom = mix(screenBloom, tintBloom, dawnAmount);

    fragColor = vec4(mix(withBloom, coreColor, inside), terminal.a);
}
