import { z } from 'zod';

export const maxImageBytes = 10 * 1024 * 1024;
const subject = z.string().regex(/^character-[0-9a-f]{32}$/);
const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/);
const revision = z.number().int().positive();
const mime = z.enum(['image/png', 'image/jpeg', 'image/webp']);
const text = (limit: number) => z.string().min(1).max(limit).refine(s => !!s.trim() && !/[\x00-\x08\x0b-\x1f]/.test(s));
export const characterBioSchema = z.strictObject({ name: text(200), age: text(80).nullable(), gender: text(80).nullable(), vibe: text(4096).nullable() });
export const characterRefSchema = z.strictObject({ subject_id: subject, revision, digest });
export const characterImageSchema = z.strictObject({ digest, mime_type: mime,
  byte_length: z.number().int().min(1).max(maxImageBytes), width: z.number().int().min(1).max(8192), height: z.number().int().min(1).max(8192),
}).refine(image => image.width * image.height <= 16_000_000);
export const characterItemSchema = z.strictObject({ ref: characterRefSchema, character: z.strictObject({
  schema_id: z.literal('character'), schema_version: z.literal('1'), subject_id: subject, revision,
  bio: characterBioSchema, images: z.array(characterImageSchema).min(1).max(6),
}) }).refine(item => item.ref.subject_id === item.character.subject_id && item.ref.revision === item.character.revision);
export const characterListSchema = z.strictObject({ items: z.array(characterItemSchema) })
  .refine(list => new Set(list.items.map(item => item.ref.subject_id)).size === list.items.length);
export const characterImageInputSchema = z.union([
  z.strictObject({ ref: characterRefSchema, image_digest: digest }),
  z.strictObject({ mime_type: mime, data_base64: z.string().min(4).max(Math.ceil(maxImageBytes / 3) * 4)
    .regex(/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/) }),
]);
export const characterMutationSchema = z.strictObject({ mutation_id: z.string().min(1).max(128).regex(/^[a-zA-Z0-9_-]+$/),
  subject_id: subject.nullable(), expected_revision: revision.nullable(), bio: characterBioSchema,
  images: z.array(characterImageInputSchema).min(1).max(6),
}).refine(m => (m.subject_id === null) === (m.expected_revision === null));
const receiptSchema = z.strictObject({ mutation_id: z.string(), ref: characterRefSchema });
export type CharacterRef = z.infer<typeof characterRefSchema>;
export type CharacterItem = z.infer<typeof characterItemSchema>;
export type CharacterMutation = z.infer<typeof characterMutationSchema>;
export type CharacterImageInput = z.infer<typeof characterImageInputSchema>;
export function sameCharacterRef(a: CharacterRef, b: CharacterRef) {
  return a.subject_id === b.subject_id && a.revision === b.revision && a.digest === b.digest;
}
export function characterExactUrl(ref: CharacterRef) {
  const exact = characterRefSchema.parse(ref);
  return `/api/characters/${exact.subject_id}?${new URLSearchParams({ revision: String(exact.revision), digest: exact.digest })}`;
}
export function characterImageUrl(ref: CharacterRef, imageDigest: string) {
  const url = characterExactUrl(ref).split('?');
  return `${url[0]}/images/${encodeURIComponent(digest.parse(imageDigest))}?${url[1]}`;
}
export function validateCharacterReceipt(value: unknown, mutation: CharacterMutation) {
  const receipt = receiptSchema.parse(value);
  if (receipt.mutation_id !== mutation.mutation_id || (mutation.subject_id !== null &&
    (receipt.ref.subject_id !== mutation.subject_id || receipt.ref.revision !== mutation.expected_revision! + 1)) ||
    (mutation.subject_id === null && receipt.ref.revision !== 1)) throw Error('Receipt не совпадает с сохранённой мутацией. Доставка не подтверждена.');
  return receipt;
}
