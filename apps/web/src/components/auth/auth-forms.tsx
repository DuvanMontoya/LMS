'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2, Eye, EyeOff, LoaderCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useId, useRef, useState } from 'react';
import {
  useForm,
  type FieldValues,
  type Path,
  type UseFormRegister,
} from 'react-hook-form';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthApiError, mapAllauthErrorToSpanish } from '@/lib/auth/errors';
import { getBrowserAuthSession } from '@/lib/auth/api';
import {
  useLogin,
  useRequestPasswordReset,
  useResendVerification,
  useResetPassword,
  useSignUp,
  useVerifyEmail,
} from '@/lib/auth/hooks';
import { sanitizeReturnPath } from '@/lib/auth/return-path';
import {
  loginSchema,
  passwordRequestSchema,
  passwordResetSchema,
  signUpSchema,
  verificationSchema,
  type LoginValues,
  type PasswordRequestValues,
  type PasswordResetValues,
  type SignUpValues,
  type VerificationValues,
} from '@/lib/auth/schemas';

type FieldProps<T extends FieldValues> = {
  name: Path<T>;
  label: string;
  register: UseFormRegister<T>;
  error?: string | undefined;
  type?: 'email' | 'password' | 'text';
  autoComplete: string;
};

function Field<T extends FieldValues>({
  name,
  label,
  register,
  error,
  type = 'text',
  autoComplete,
}: FieldProps<T>) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="auth-field">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type={type}
        autoComplete={autoComplete}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className="auth-control"
        {...register(name)}
      />
      {error ? (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function PasswordField<T extends FieldValues>(
  props: Omit<FieldProps<T>, 'type'>,
) {
  const [visible, setVisible] = useState(false);
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className="auth-field">
      <Label htmlFor={id}>{props.label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={visible ? 'text' : 'password'}
          autoComplete={props.autoComplete}
          aria-invalid={Boolean(props.error)}
          aria-describedby={props.error ? errorId : undefined}
          className="auth-control pr-14"
          {...props.register(props.name)}
        />
        <Button
          type="button"
          aria-pressed={visible}
          aria-label={
            visible ? 'Ocultar clave de acceso' : 'Mostrar clave de acceso'
          }
          onClick={() => setVisible((current) => !current)}
          className="auth-password-toggle"
          size="icon"
          variant="ghost"
        >
          {visible ? <EyeOff /> : <Eye />}
        </Button>
      </div>
      {props.error ? (
        <p id={errorId} className="text-sm text-destructive">
          {props.error}
        </p>
      ) : null}
    </div>
  );
}

function ErrorSummary({ message }: Readonly<{ message: string | null }>) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (message) ref.current?.focus();
  }, [message]);
  if (!message) return null;
  return (
    <Alert
      ref={ref}
      tabIndex={-1}
      role="alert"
      aria-live="assertive"
      variant="destructive"
    >
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

function StatusSummary({ message }: Readonly<{ message: string | null }>) {
  if (!message) return null;
  return (
    <Alert className="border-emerald-600/20 bg-emerald-500/5" role="status">
      <CheckCircle2 className="text-emerald-700" />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

function submitError<T extends FieldValues>(
  error: unknown,
  setError: ReturnType<typeof useForm<T>>['setError'],
): string {
  if (!(error instanceof AuthApiError))
    return mapAllauthErrorToSpanish('unknown', null);
  for (const [field, code] of Object.entries(error.fieldErrors)) {
    if (field === 'email' || field === 'password' || field === 'key') {
      const formField = field === 'key' ? 'code' : field;
      setError(formField as Path<T>, {
        message: mapAllauthErrorToSpanish('validation', code),
      });
    }
  }
  return error.message;
}

function useHydrated() {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => {
    setHydrated(true);
  }, []);
  return hydrated;
}

function SubmitButton({
  pending,
  hydrated = true,
  children,
}: Readonly<{ pending: boolean; hydrated?: boolean; children: string }>) {
  return (
    <Button
      type="submit"
      disabled={pending || !hydrated}
      className="auth-submit"
    >
      {pending || !hydrated ? <LoaderCircle className="animate-spin" /> : null}
      {!hydrated
        ? 'Preparando formulario seguro…'
        : pending
          ? 'Enviando…'
          : children}
    </Button>
  );
}

export function LoginForm({
  registrationAvailable = true,
}: Readonly<{ registrationAvailable?: boolean }>) {
  const searchParams = useSearchParams();
  const login = useLogin();
  const hydrated = useHydrated();
  const [message, setMessage] = useState<string | null>(null);
  const statusMessage =
    searchParams.get('reset') === '1'
      ? 'Tu contraseña fue actualizada. Ya puedes iniciar sesión.'
      : searchParams.get('verified') === '1'
        ? 'Tu correo fue verificado. Ya puedes iniciar sesión.'
        : null;
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });
  const onSubmit = async ({ email, password }: LoginValues) => {
    setMessage(null);
    try {
      await login.mutateAsync({ email, password });
      form.reset({ email, password: '' });
      // A full navigation starts a new server request with the session cookie.
      // Client-side route reuse can otherwise render the anonymous access
      // context immediately after a successful login.
      window.location.assign(sanitizeReturnPath(searchParams.get('next')));
    } catch (error) {
      setMessage(submitError(error, form.setError));
    }
  };
  return (
    <form
      method="post"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
      className="auth-form-grid"
    >
      <StatusSummary message={statusMessage} />
      <ErrorSummary message={message} />
      <Field
        name="email"
        label="Correo electrónico"
        type="email"
        autoComplete="email"
        register={form.register}
        error={form.formState.errors.email?.message}
      />
      <PasswordField
        name="password"
        label="Contraseña"
        autoComplete="current-password"
        register={form.register}
        error={form.formState.errors.password?.message}
      />
      <SubmitButton pending={login.isPending} hydrated={hydrated}>
        Iniciar sesión
      </SubmitButton>
      <nav className="auth-form-links">
        <Link
          className="font-medium text-primary underline-offset-4 hover:underline"
          href="/auth/recuperar-contrasena"
        >
          ¿Olvidaste tu contraseña?
        </Link>
        {registrationAvailable ? (
          <Link
            className="font-medium text-primary underline-offset-4 hover:underline"
            href="/auth/registro"
          >
            Crear una cuenta
          </Link>
        ) : null}
      </nav>
    </form>
  );
}

export function SignUpForm() {
  const router = useRouter();
  const signUp = useSignUp();
  const hydrated = useHydrated();
  const [message, setMessage] = useState<string | null>(null);
  const form = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: { email: '', password: '', confirmation: '' },
  });
  const onSubmit = async ({ email, password }: SignUpValues) => {
    setMessage(null);
    try {
      await signUp.mutateAsync({ email, password });
      form.reset({ email, password: '', confirmation: '' });
      router.replace('/auth/verificar-correo');
    } catch (error) {
      setMessage(submitError(error, form.setError));
    }
  };
  return (
    <form
      method="post"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
      className="auth-form-grid"
    >
      <ErrorSummary message={message} />
      <Field
        name="email"
        label="Correo electrónico"
        type="email"
        autoComplete="email"
        register={form.register}
        error={form.formState.errors.email?.message}
      />
      <PasswordField
        name="password"
        label="Contraseña nueva"
        autoComplete="new-password"
        register={form.register}
        error={form.formState.errors.password?.message}
      />
      <PasswordField
        name="confirmation"
        label="Confirmar contraseña"
        autoComplete="new-password"
        register={form.register}
        error={form.formState.errors.confirmation?.message}
      />
      <SubmitButton pending={signUp.isPending} hydrated={hydrated}>
        Crear cuenta
      </SubmitButton>
      <p className="text-sm">
        ¿Ya tienes cuenta?{' '}
        <Link className="underline" href="/auth/iniciar-sesion">
          Inicia sesión
        </Link>
        .
      </p>
    </form>
  );
}

export function VerifyEmailForm() {
  const router = useRouter();
  const verify = useVerifyEmail();
  const resend = useResendVerification();
  const hydrated = useHydrated();
  const [message, setMessage] = useState<string | null>(null);
  const form = useForm<VerificationValues>({
    resolver: zodResolver(verificationSchema),
    defaultValues: { code: '' },
  });
  const onSubmit = async ({ code }: VerificationValues) => {
    setMessage(null);
    try {
      await verify.mutateAsync({ code });
      form.reset({ code: '' });
      const session = await getBrowserAuthSession();
      router.replace(
        session.kind === 'authenticated'
          ? '/estudiar'
          : '/auth/iniciar-sesion?verified=1',
      );
    } catch (error) {
      setMessage(submitError(error, form.setError));
    }
  };
  const onResend = async () => {
    setMessage(null);
    try {
      await resend.mutateAsync();
      setMessage('Enviamos un nuevo código si el proceso sigue activo.');
    } catch (error) {
      setMessage(submitError(error, form.setError));
    }
  };
  return (
    <form
      method="post"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
      className="auth-form-grid"
    >
      <ErrorSummary message={message} />
      <Field
        name="code"
        label="Código de verificación"
        autoComplete="one-time-code"
        register={form.register}
        error={form.formState.errors.code?.message}
      />
      <SubmitButton pending={verify.isPending} hydrated={hydrated}>
        Verificar correo
      </SubmitButton>
      <Button
        type="button"
        disabled={resend.isPending}
        onClick={onResend}
        className="h-11 w-full"
        variant="outline"
      >
        {resend.isPending ? 'Reenviando…' : 'Reenviar código'}
      </Button>
      <p className="text-sm">
        <Link className="underline" href="/auth/iniciar-sesion">
          Volver a inicio de sesión
        </Link>
      </p>
    </form>
  );
}

export function PasswordRequestForm() {
  const router = useRouter();
  const request = useRequestPasswordReset();
  const hydrated = useHydrated();
  const [message, setMessage] = useState<string | null>(null);
  const form = useForm<PasswordRequestValues>({
    resolver: zodResolver(passwordRequestSchema),
    defaultValues: { email: '' },
  });
  const onSubmit = async ({ email }: PasswordRequestValues) => {
    setMessage(null);
    try {
      await request.mutateAsync({ email });
      router.replace('/auth/restablecer-contrasena?sent=1');
    } catch (error) {
      setMessage(submitError(error, form.setError));
    }
  };
  return (
    <form
      method="post"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
      className="auth-form-grid"
    >
      <ErrorSummary message={message} />
      <Field
        name="email"
        label="Correo electrónico"
        type="email"
        autoComplete="email"
        register={form.register}
        error={form.formState.errors.email?.message}
      />
      <SubmitButton pending={request.isPending} hydrated={hydrated}>
        Solicitar código
      </SubmitButton>
      <p className="text-sm">
        <Link className="underline" href="/auth/iniciar-sesion">
          Volver a inicio de sesión
        </Link>
      </p>
    </form>
  );
}

export function PasswordResetForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reset = useResetPassword();
  const hydrated = useHydrated();
  const [message, setMessage] = useState<string | null>(null);
  const form = useForm<PasswordResetValues>({
    resolver: zodResolver(passwordResetSchema),
    defaultValues: { code: '', password: '', confirmation: '' },
  });
  const onSubmit = async ({ code, password }: PasswordResetValues) => {
    setMessage(null);
    try {
      await reset.mutateAsync({ code, password });
      form.reset({ code: '', password: '', confirmation: '' });
      router.replace('/auth/iniciar-sesion?reset=1');
    } catch (error) {
      setMessage(submitError(error, form.setError));
    }
  };
  return (
    <form
      method="post"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
      className="auth-form-grid"
    >
      <StatusSummary
        message={
          searchParams.get('sent') === '1'
            ? 'Código enviado. Escríbelo abajo junto con tu contraseña nueva antes de que venza.'
            : null
        }
      />
      <ErrorSummary message={message} />
      <ol className="space-y-1 rounded-lg border bg-muted/30 p-4 text-sm leading-6 text-muted-foreground">
        <li>
          <strong className="text-foreground">1.</strong> Revisa el correo y la
          carpeta de spam.
        </li>
        <li>
          <strong className="text-foreground">2.</strong> Copia el código de un
          solo uso; vence en 3 minutos.
        </li>
        <li>
          <strong className="text-foreground">3.</strong> Escríbelo aquí y
          define tu contraseña nueva.
        </li>
      </ol>
      <Field
        name="code"
        label="Código recibido"
        autoComplete="one-time-code"
        register={form.register}
        error={form.formState.errors.code?.message}
      />
      <PasswordField
        name="password"
        label="Nueva contraseña"
        autoComplete="new-password"
        register={form.register}
        error={form.formState.errors.password?.message}
      />
      <PasswordField
        name="confirmation"
        label="Confirmar contraseña"
        autoComplete="new-password"
        register={form.register}
        error={form.formState.errors.confirmation?.message}
      />
      <SubmitButton pending={reset.isPending} hydrated={hydrated}>
        Restablecer contraseña
      </SubmitButton>
      <p className="text-sm">
        <Link className="underline" href="/auth/iniciar-sesion">
          Iniciar sesión
        </Link>
        {' · '}
        <Link className="underline" href="/auth/recuperar-contrasena">
          Solicitar otro código
        </Link>
      </p>
    </form>
  );
}
