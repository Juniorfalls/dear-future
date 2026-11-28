import React from 'react';
import * as THREE from 'three';

/**
 * Stylized (plush, not photoreal) mantis shrimp.
 *
 * Built from primitives only — capsules, spheres, tubes — following the
 * img2threejs rule "reconstruction-by-code, never downloaded meshes". Proportions
 * come from 3d/mantis-shrimp/object-sculpt-spec.json: a segmented carapace with
 * colour bands, stalked compound eyes, folded raptorial clubs, eight paddle legs
 * and a five-blade tail fan.
 *
 * Everything is driven by `time` (seconds) and `punch` (0..1) so the render is a
 * pure function of the Remotion frame.
 */

const SHELL = {
  teal: '#3aa79f',
  tealDark: '#1f6d70',
  magenta: '#c4577f',
  plum: '#7c3a63',
  club: '#e2764f',
  clubDark: '#b0512f',
  eye: '#f2efe4',
  pupil: '#141b1f',
  leg: '#d8a06a',
};

const BANDS = [SHELL.tealDark, SHELL.magenta, SHELL.teal, SHELL.plum, SHELL.club];

const SEGMENTS: {x: number; r: number; len: number}[] = [
  {x: 1.02, r: 0.3, len: 0.22},
  {x: 0.62, r: 0.38, len: 0.26},
  {x: 0.16, r: 0.36, len: 0.28},
  {x: -0.32, r: 0.28, len: 0.26},
  {x: -0.72, r: 0.2, len: 0.22},
];

const LEG_X = [0.78, 0.42, 0.02, -0.38, -0.72];

const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

const Stalk: React.FC<{
  eye: {x: number; y: number; z: number};
  tilt: number;
  look: number;
  s: number;
}> = ({eye, tilt, look, s}) => (
  <group position={[eye.x, eye.y, eye.z]} rotation={[0, 0, tilt]}>
    <mesh>
      <cylinderGeometry args={[0.045 * s, 0.06 * s, 0.34 * s, 10]} />
      <meshStandardMaterial color={SHELL.tealDark} roughness={0.6} />
    </mesh>
    <group position={[0, 0.17 * s, 0]} rotation={[0, look, 0]}>
      <mesh>
        <sphereGeometry args={[0.135 * s, 18, 14]} />
        <meshStandardMaterial color={SHELL.eye} roughness={0.28} metalness={0.05} />
      </mesh>
      <mesh position={[0.075 * s, 0.02 * s, 0.045 * s]} scale={[0.55, 1, 1]}>
        <sphereGeometry args={[0.062 * s, 12, 10]} />
        <meshStandardMaterial color={SHELL.pupil} roughness={0.15} metalness={0.35} />
      </mesh>
      <mesh position={[0.02 * s, 0.09 * s, 0.09 * s]}>
        <sphereGeometry args={[0.026 * s, 8, 8]} />
        <meshStandardMaterial color="#ffffff" roughness={0.1} />
      </mesh>
    </group>
  </group>
);

const Club: React.FC<{side: number; punch: number; s: number; flash: number}> = ({side, punch, s, flash}) => {
  // punch 0 -> rest, rises to 1 on the strike, then eases back to rest.
  // The propodus cocks under the body, then drives forward and slightly up,
  // which is how the real raptorial appendage fires.
  const cock = Math.sin(clamp01(punch) * Math.PI) * 0.9;
  const strike = easeOut(clamp01((punch - 0.5) / 0.5));
  const angle = -0.95 - cock * 0.5 + strike * 0.85;
  return (
    <group
      position={[(1.16 + strike * 0.26) * s, (-0.1 + strike * 0.06) * s, 0.3 * s * side]}
      rotation={[0, 0, angle]}
    >
      <mesh position={[0.16 * s, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <capsuleGeometry args={[0.095 * s, 0.2 * s, 6, 12]} />
        <meshStandardMaterial color={SHELL.clubDark} roughness={0.55} />
      </mesh>
      <group position={[0.3 * s, 0.02 * s, 0]} rotation={[0, 0, 0.55 - cock * 0.5 + strike * 0.35]}>
        <mesh position={[0.12 * s, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <capsuleGeometry args={[0.075 * s, 0.16 * s, 6, 12]} />
          <meshStandardMaterial color={SHELL.club} roughness={0.5} />
        </mesh>
        <mesh position={[0.27 * s, 0, 0]} scale={[1.25, 1, 1]}>
          <sphereGeometry args={[0.145 * s, 16, 12]} />
          <meshStandardMaterial
            color={SHELL.club}
            roughness={0.42}
            metalness={0.06}
            emissive={SHELL.clubDark}
            emissiveIntensity={0.12 + flash * 1.6}
          />
        </mesh>
        {flash > 0.04 ? (
          <mesh position={[0.42 * s, 0, 0]}>
            <sphereGeometry args={[(0.14 + flash * 0.1) * s, 12, 10]} />
            <meshBasicMaterial color="#eafaff" transparent opacity={0.75 * flash} blending={2} depthWrite={false} />
          </mesh>
        ) : null}
      </group>
    </group>
  );
};

const Leg: React.FC<{x: number; side: number; paddle: number; s: number}> = ({x, side, paddle, s}) => (
  <group position={[x * s, -0.24 * s, 0.26 * s * side]} rotation={[side * 0.55, 0, paddle]}>
    <mesh position={[0, -0.12 * s, 0]}>
      <capsuleGeometry args={[0.045 * s, 0.2 * s, 5, 10]} />
      <meshStandardMaterial color={SHELL.leg} roughness={0.7} />
    </mesh>
    <mesh position={[0, -0.26 * s, -0.05 * s * side]} rotation={[side * 0.7, 0, 0.3]}>
      <capsuleGeometry args={[0.035 * s, 0.14 * s, 5, 10]} />
      <meshStandardMaterial color={SHELL.leg} roughness={0.7} />
    </mesh>
  </group>
);

export const MantisShrimp: React.FC<{
  time: number;
  punch: number;
  flash?: number;
  scale?: number;
}> = ({time, punch, flash = 0, scale = 1}) => {
  const s = scale;
  const breathe = 1 + Math.sin(time * 1.6) * 0.02;
  const float = Math.sin(time * 1.15) * 0.16;
  const roll = Math.sin(time * 0.9) * 0.06;
  const pitch = Math.sin(time * 0.7 + 0.6) * 0.04;
  const look = Math.sin(time * 0.45) * 0.28 + Math.sin(time * 1.9) * 0.05;

  return (
    <group position={[0, float, 0]} rotation={[pitch, 0, roll]} scale={breathe}>
      {/* carapace segments */}
      {SEGMENTS.map((seg, i) => {
        const wave = Math.sin(time * 2.2 - i * 0.55) * 0.05;
        return (
          <group key={i} position={[seg.x * s, Math.sin(time * 1.4 - i * 0.4) * 0.03 * s, wave * 0.1]} rotation={[0, wave, 0]}>
            <mesh rotation={[0, 0, Math.PI / 2]} scale={[1, 1, 0.82]}>
              <capsuleGeometry args={[seg.r * s, seg.len * s, 10, 22]} />
              <meshStandardMaterial
                color={BANDS[i % BANDS.length]}
                roughness={0.5}
                metalness={0.08}
                emissive={BANDS[i % BANDS.length]}
                emissiveIntensity={0.06}
              />
            </mesh>
            {/* dorsal ridge */}
            <mesh position={[0, seg.r * 0.72 * s, 0]} scale={[1.5, 0.35, 0.9]}>
              <sphereGeometry args={[seg.r * 0.5 * s, 14, 10]} />
              <meshStandardMaterial color={SHELL.tealDark} roughness={0.55} />
            </mesh>
          </group>
        );
      })}

      {/* head + helmet */}
      <group position={[1.34 * s, Math.sin(time * 1.4) * 0.02 * s, 0]}>
        <mesh>
          <sphereGeometry args={[0.38 * s, 22, 18]} />
          <meshStandardMaterial color={SHELL.teal} roughness={0.48} metalness={0.1} emissive={SHELL.tealDark} emissiveIntensity={0.08} />
        </mesh>
        <mesh position={[0.1 * s, 0.06 * s, 0]} scale={[1.1, 0.78, 1.02]}>
          <sphereGeometry args={[0.3 * s, 18, 14]} />
          <meshStandardMaterial color={SHELL.magenta} roughness={0.45} />
        </mesh>
        {/* mouth plates */}
        <mesh position={[0.34 * s, -0.13 * s, 0]} scale={[0.8, 0.5, 0.9]}>
          <sphereGeometry args={[0.14 * s, 14, 10]} />
          <meshStandardMaterial color={SHELL.clubDark} roughness={0.6} />
        </mesh>
      </group>

      {/* eyes on stalks */}
      <Stalk eye={{x: 1.42 * s, y: 0.26 * s, z: 0.2 * s}} tilt={0.55} look={look} s={s} />
      <Stalk eye={{x: 1.42 * s, y: 0.26 * s, z: -0.2 * s}} tilt={-0.55} look={look} s={s} />

      {/* antennae */}
      {[1, -1].map((side) => {
        const sway = Math.sin(time * 1.5 + side) * 0.12;
        return (
          <group key={side} position={[1.5 * s, 0.12 * s, 0.16 * s * side]} rotation={[0, sway, 0.15]}>
            <mesh rotation={[0, 0, -0.35]}>
              <cylinderGeometry args={[0.016 * s, 0.026 * s, 1.15 * s, 8]} />
              <meshStandardMaterial color={SHELL.tealDark} roughness={0.6} />
            </mesh>
            <mesh position={[0.5 * s, 0.52 * s, 0.04 * s * side]} rotation={[0, 0, -1.1]}>
              <cylinderGeometry args={[0.008 * s, 0.016 * s, 0.55 * s, 8]} />
              <meshStandardMaterial color={SHELL.magenta} roughness={0.55} />
            </mesh>
          </group>
        );
      })}

      {/* raptorial clubs */}
      <Club side={1} punch={punch} s={s} flash={flash} />
      <Club side={-1} punch={punch} s={s} flash={flash} />

      {/* walking legs */}
      {LEG_X.map((x, i) =>
        [1, -1].map((side) => (
          <Leg key={`${i}-${side}`} x={x} side={side} s={s} paddle={Math.sin(time * 3.1 + i * 0.8 + (side > 0 ? 0 : Math.PI)) * 0.22} />
        )),
      )}

      {/* tail fan */}
      <group position={[-0.95 * s, 0, 0]}>
        {[-2, -1, 0, 1, 2].map((k) => (
          <mesh
            key={k}
            position={[-0.18 * s, 0.06 * k * s, 0.16 * k * s]}
            rotation={[Math.PI / 2 - k * 0.28, 0, -0.5 + Math.sin(time * 1.8 + k) * 0.05]}
            scale={[1, 1, 0.32]}
          >
            <coneGeometry args={[0.13 * s, 0.5 * s, 8]} />
            <meshStandardMaterial color={k === 0 ? SHELL.club : SHELL.plum} roughness={0.55} />
          </mesh>
        ))}
      </group>
    </group>
  );
};

export const MANTIS_COLORS = SHELL;
export const MANTIS_THREE = {THREE};
