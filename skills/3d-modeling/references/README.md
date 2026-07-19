# 3D Modeling — Reference

## Shader Examples

```glsl
// Vertex displacement shader
void main() {
    vec3 pos = position;
    pos.y += sin(pos.x * 2.0 + uTime) * 0.1;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
}
```

```glsl
// Fresnel rim glow (fragment)
void main() {
    float rim = 1.0 - max(0.0, dot(vNormal, vViewDir));
    rim = pow(rim, 3.0);
    gl_FragColor = vec4(rim * vec3(0.3, 0.6, 1.0), rim);
}
```

## Performance Tuning — Large Scenes

| Technique | Impact | Trade-off |
|-----------|--------|-----------|
| LOD | High | More memory from duplicate meshes |
| Frustum culling | Medium | CPU overhead for bounds checks |
| GPU instancing | Very High | Static transforms only |
| Texture atlasing | Medium | UV layout complexity |
| Draw-call merging | High | Loses per-object culling |

- Keep per-object vertices under 65k for WebGL compatibility.
- Prefer indexed `BufferGeometry` over non-indexed (saves 30-50% GPU memory).
- Use `mergeGeometries` for static, non-moving objects sharing a material.

## Model Format Compatibility

| Format | Binary | Anim | UVs | Materials | Best For |
|--------|--------|------|-----|-----------|----------|
| glTF 2.0 | .glb | Yes | Yes | PBR | Web, real-time |
| OBJ | No | No | Yes | Limited | Interchange |
| FBX | Yes | Yes | Yes | Yes | DCC pipelines |
| STL | Yes | No | No | No | 3D printing |
| PLY | Yes | No | Yes | No | Point clouds |

- **Prefer glTF/GLB** for web deployment (native Three.js, Babylon.js, Model Viewer support).
- Convert FBX to glTF: `FBX2glTF --binary --input scene.fbx --output scene.glb`.
- Validate glTF output with `gltf-validator` before committing to the pipeline.
