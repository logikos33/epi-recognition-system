import { BarChart3 } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Dashboard e Relatórios</h1>
        <p className="text-text-secondary mt-1">
          Visualize estatísticas e métricas do sistema de detecção
        </p>
      </div>

      <Card className="border border-border">
        <CardContent className="p-12 flex flex-col items-center justify-center text-center">
          <BarChart3 className="w-16 h-16 text-text-muted mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Página em Desenvolvimento
          </h2>
          <p className="text-text-secondary max-w-md">
            Esta funcionalidade será implementada em breve. Você poderá visualizar
            gráficos de detecções, relatórios de desempenho e estatísticas detalhadas.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
