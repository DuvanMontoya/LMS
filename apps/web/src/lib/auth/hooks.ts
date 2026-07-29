'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  getBrowserAuthSession,
  login,
  logout,
  requestPasswordReset,
  resendVerification,
  resetPassword,
  signUp,
  verifyEmail,
} from './api';
import { authKeys } from '@/lib/query/auth-keys';

export function useAuthSession() {
  return useQuery({
    queryKey: authKeys.session(),
    queryFn: getBrowserAuthSession,
  });
}

export function useSignUp() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      signUp(email, password),
  });
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: ({ code }: { code: string }) => verifyEmail(code),
  });
}

export function useResendVerification() {
  return useMutation({ mutationFn: resendVerification });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: authKeys.session() }),
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: async () => {
      await queryClient.cancelQueries({ queryKey: authKeys.session() });
      queryClient.removeQueries({ queryKey: authKeys.session() });
    },
  });
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: ({ email }: { email: string }) => requestPasswordReset(email),
  });
}

export function useResetPassword() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ code, password }: { code: string; password: string }) =>
      resetPassword(code, password),
    onSuccess: () =>
      queryClient.removeQueries({ queryKey: authKeys.session() }),
  });
}
