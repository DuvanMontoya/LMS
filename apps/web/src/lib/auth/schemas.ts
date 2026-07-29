import { z } from 'zod';

const email = z
  .string()
  .trim()
  .email('Ingresa un correo electrónico válido.')
  .max(254);
const password = z.string().min(1, 'Ingresa una contraseña.').max(1024);
const code = z.string().trim().min(1, 'Ingresa el código recibido.').max(128);

export const loginSchema = z.object({ email, password });
export const signUpSchema = z
  .object({ email, password, confirmation: password })
  .refine((values) => values.password === values.confirmation, {
    message: 'Las contraseñas no coinciden.',
    path: ['confirmation'],
  });
export const verificationSchema = z.object({ code });
export const passwordRequestSchema = z.object({ email });
export const passwordResetSchema = z
  .object({ code, password, confirmation: password })
  .refine((values) => values.password === values.confirmation, {
    message: 'Las contraseñas no coinciden.',
    path: ['confirmation'],
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type SignUpValues = z.infer<typeof signUpSchema>;
export type VerificationValues = z.infer<typeof verificationSchema>;
export type PasswordRequestValues = z.infer<typeof passwordRequestSchema>;
export type PasswordResetValues = z.infer<typeof passwordResetSchema>;
