import { AuthShell } from '@/components/auth/auth-shell';
import { ManagedAccountActivation } from '@/components/auth/managed-account-activation';

export default function ManagedAccountActivationPage() {
  return (
    <AuthShell
      description="Establece una contraseña personal. La institución no conoce ni recibe este valor."
      title="Activar cuenta institucional"
    >
      <ManagedAccountActivation />
    </AuthShell>
  );
}
