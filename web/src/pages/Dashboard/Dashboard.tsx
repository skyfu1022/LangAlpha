import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ListFilter } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { useIsMobile } from '@/hooks/useIsMobile';
import DashboardHeader from './components/DashboardHeader';
import ConfirmDialog from './components/ConfirmDialog';
import IndexMovementCard from './components/IndexMovementCard';
import AIDailyBriefCard from './components/AIDailyBriefCard';
import NewsFeedCard from './components/NewsFeedCard';
import ChatInputCard from './components/ChatInputCard';
import EarningsCalendarCard from './components/EarningsCalendarCard';
import PortfolioWatchlistCard from './components/PortfolioWatchlistCard';
import NewsDetailModal from './components/NewsDetailModal';
import InsightDetailModal from './components/InsightDetailModal';
import AddWatchlistItemDialog from './components/AddWatchlistItemDialog';
import AddPortfolioHoldingDialog from './components/AddPortfolioHoldingDialog';
import { useWatchlistData } from './hooks/useWatchlistData';
import { usePortfolioData } from './hooks/usePortfolioData';
import { useTickerNews } from './hooks/useTickerNews';
import { useDashboardData } from './hooks/useDashboardData';
import { useOnboarding, setOnboardingIgnoredFor24h } from './hooks/useOnboarding';
import './Dashboard.css';

interface DeleteConfirmState {
  open: boolean;
  title: string;
  message: string;
  onConfirm: (() => Promise<void>) | null;
}

function Dashboard() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  // News modal state
  const [selectedNewsId, setSelectedNewsId] = useState<string | null>(null);

  // Insight modal state
  const [selectedMarketInsightId, setSelectedMarketInsightId] = useState<string | null>(null);

  // Mobile watchlist bottom sheet
  const [showWatchlistSheet, setShowWatchlistSheet] = useState(false);

  const {
    indices,
    indicesLoading,
    newsItems,
    newsLoading,
    marketStatus,
  } = useDashboardData();

  const {
    showOnboardingDialog,
    setShowOnboardingDialog,
    isCreatingWorkspace,
    navigateToOnboarding,
    navigateToModifyPreferences
  } = useOnboarding();

  const watchlist = useWatchlistData();
  const portfolio = usePortfolioData();

  const portfolioNews = useTickerNews(portfolio.rows, 'portfolio');
  const watchlistNews = useTickerNews(watchlist.rows, 'watchlist');

  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirmState>({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  });

  const handleDeletePortfolioItem = useCallback(
    (holdingId: string) => {
      setDeleteConfirm(portfolio.handleDelete(holdingId) as DeleteConfirmState);
    },
    [portfolio.handleDelete]
  );

  const runDeleteConfirm = useCallback(async () => {
    if (deleteConfirm.onConfirm) await deleteConfirm.onConfirm();
    setDeleteConfirm((p) => ({ ...p, open: false }));
  }, [deleteConfirm.onConfirm]);

  return (
    <div className="dashboard-container min-h-screen">
      {/* Main content area */}
      <main className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        <DashboardHeader />

        <div className="mx-auto max-w-[1920px] w-full p-3 sm:p-6 pb-32">
          {/* Market Overview heading + mobile watchlist tab */}
          <div className="flex items-center justify-between mb-6">
            <h1
              className="text-2xl font-bold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              Market Overview
            </h1>
            {isMobile && (
              <button
                onClick={() => setShowWatchlistSheet(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors"
                style={{
                  borderColor: 'var(--color-border-muted)',
                  color: 'var(--color-text-secondary)',
                  backgroundColor: 'var(--color-bg-card)',
                }}
              >
                <ListFilter size={13} />
                Watchlist
              </button>
            )}
          </div>

          {/* Index Movement — full width */}
          <div className="mb-8">
            <IndexMovementCard indices={indices} loading={indicesLoading} />
          </div>

          {/* 3-column grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left 2/3 */}
            <div className="lg:col-span-2 space-y-8">
              <AIDailyBriefCard onReadFull={setSelectedMarketInsightId} />
              <NewsFeedCard
                marketItems={newsItems}
                marketLoading={newsLoading}
                portfolioItems={portfolioNews.items}
                portfolioLoading={portfolioNews.loading}
                watchlistItems={watchlistNews.items}
                watchlistLoading={watchlistNews.loading}
                onNewsClick={(id) => setSelectedNewsId(String(id))}
              />
            </div>

            {/* Right 1/3 — sticky sidebar (hidden on mobile, accessible via sheet) */}
            {!isMobile && (
              <div className="lg:col-span-1">
                <div className="lg:sticky lg:top-24 space-y-6">
                  <div>
                    <PortfolioWatchlistCard
                      watchlistRows={watchlist.rows}
                      watchlistLoading={watchlist.loading}
                      onWatchlistAdd={() => watchlist.setModalOpen(true)}
                      onWatchlistDelete={watchlist.handleDelete}
                      portfolioRows={portfolio.rows}
                      portfolioLoading={portfolio.loading}
                      hasRealHoldings={portfolio.hasRealHoldings}
                      onPortfolioAdd={() => portfolio.setModalOpen(true)}
                      onPortfolioDelete={handleDeletePortfolioItem}
                      onPortfolioEdit={portfolio.openEdit}
                      marketStatus={marketStatus}
                    />
                  </div>
                  <EarningsCalendarCard />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Floating chat */}
        <ChatInputCard />
      </main>

      {/* News Detail Modal */}
      <NewsDetailModal newsId={selectedNewsId} onClose={() => setSelectedNewsId(null)} />

      {/* Insight Detail Modal */}
      {selectedMarketInsightId && (
        <InsightDetailModal
          marketInsightId={selectedMarketInsightId}
          onClose={() => setSelectedMarketInsightId(null)}
        />
      )}

      {/* Dialogs */}
      <ConfirmDialog
        open={deleteConfirm.open}
        title={deleteConfirm.title}
        message={deleteConfirm.message}
        confirmLabel={t('common.delete')}
        onConfirm={runDeleteConfirm}
        onOpenChange={(open) => !open && setDeleteConfirm((p) => ({ ...p, open: false }))}
      />

      {/* Onboarding Incomplete Dialog */}
      <Dialog open={showOnboardingDialog} onOpenChange={setShowOnboardingDialog}>
        <DialogContent className="sm:max-w-md border" style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border-elevated)' }}>
          <DialogHeader>
            <DialogTitle className="title-font" style={{ color: 'var(--color-text-primary)' }}>
              {t('dashboard.prefIncomplete')}
            </DialogTitle>
            <DialogDescription style={{ color: 'var(--color-text-secondary)' }}>
              {t('dashboard.prefIncompleteMsg')}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={() => {
                setOnboardingIgnoredFor24h();
                setShowOnboardingDialog(false);
              }}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors"
              style={{ color: 'var(--color-text-primary)' }}
            >
              {t('dashboard.ignoreFor24h')}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowOnboardingDialog(false);
                navigateToOnboarding();
              }}
              disabled={isCreatingWorkspace}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-on-accent)' }}
            >
              {isCreatingWorkspace ? t('dashboard.settingUp') : t('dashboard.proceed')}
            </button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Portfolio Edit Dialog */}
      <Dialog open={!!portfolio.editRow} onOpenChange={(open) => !open && (portfolio.openEdit as (row: unknown) => void)(null)}>
        <DialogContent className="sm:max-w-sm border" style={{ backgroundColor: 'var(--color-bg-elevated)', borderColor: 'var(--color-border-elevated)' }}>
          <DialogHeader>
            <DialogTitle className="title-font" style={{ color: 'var(--color-text-primary)' }}>Edit holding — {portfolio.editRow?.symbol}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2" onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); portfolio.handleUpdate?.(); } }}>
            <div>
              <label className="text-xs block mb-1" style={{ color: 'var(--color-text-secondary)' }}>Quantity *</label>
              <Input
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 10.5"
                value={portfolio.editForm.quantity ?? ''}
                onChange={(e) => portfolio.setEditForm?.({ ...portfolio.editForm, quantity: e.target.value })}
                className="border"
                style={{ backgroundColor: 'var(--color-bg-card)', borderColor: 'var(--color-border-default)', color: 'var(--color-text-primary)' }}
              />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: 'var(--color-text-secondary)' }}>Average Cost Per Share *</label>
              <Input
                type="number"
                min="0"
                step="any"
                placeholder="e.g. 175.50"
                value={portfolio.editForm.averageCost ?? ''}
                onChange={(e) => portfolio.setEditForm?.({ ...portfolio.editForm, averageCost: e.target.value })}
                className="border"
                style={{ backgroundColor: 'var(--color-bg-card)', borderColor: 'var(--color-border-default)', color: 'var(--color-text-primary)' }}
              />
            </div>
            <div>
              <label className="text-xs block mb-1" style={{ color: 'var(--color-text-secondary)' }}>Notes</label>
              <Input
                placeholder="Optional"
                value={portfolio.editForm.notes ?? ''}
                onChange={(e) => portfolio.setEditForm?.({ ...portfolio.editForm, notes: e.target.value })}
                className="border"
                style={{ backgroundColor: 'var(--color-bg-card)', borderColor: 'var(--color-border-default)', color: 'var(--color-text-primary)' }}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => (portfolio.openEdit as (row: unknown) => void)(null)} className="px-3 py-1.5 rounded text-sm border hover:bg-foreground/10" style={{ color: 'var(--color-text-primary)', borderColor: 'var(--color-border-default)' }}>
              Cancel
            </button>
            <button type="button" onClick={portfolio.handleUpdate} className="px-3 py-1.5 rounded text-sm font-medium hover:opacity-90" style={{ backgroundColor: 'var(--color-accent-primary)', color: 'var(--color-text-on-accent)' }}>
              Save
            </button>
          </div>
        </DialogContent>
      </Dialog>

      <AddWatchlistItemDialog
        open={watchlist.modalOpen}
        onClose={() => watchlist.setModalOpen(false)}
        onAdd={watchlist.handleAdd as (...args: unknown[]) => void}
        watchlistId={watchlist.currentWatchlistId ?? undefined}
      />
      <AddPortfolioHoldingDialog
        open={portfolio.modalOpen}
        onClose={() => portfolio.setModalOpen(false)}
        onAdd={portfolio.handleAdd as (...args: unknown[]) => void}
      />

      {/* Mobile watchlist/portfolio bottom sheet */}
      <AnimatePresence>
        {showWatchlistSheet && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40"
              style={{ backgroundColor: 'var(--color-bg-overlay)' }}
              onClick={() => setShowWatchlistSheet(false)}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="fixed bottom-0 left-0 right-0 z-50 rounded-t-2xl border-t"
              style={{
                backgroundColor: 'var(--color-bg-card)',
                borderColor: 'var(--color-border-muted)',
                maxHeight: '80vh',
              }}
            >
              {/* Drag handle */}
              <div className="flex justify-center pt-3 pb-2">
                <div
                  className="w-10 h-1 rounded-full"
                  style={{ backgroundColor: 'var(--color-border-default)' }}
                />
              </div>
              <div
                className="overflow-y-auto px-4 pb-8"
                style={{ maxHeight: 'calc(80vh - 36px)' }}
              >
                <PortfolioWatchlistCard
                  watchlistRows={watchlist.rows}
                  watchlistLoading={watchlist.loading}
                  onWatchlistAdd={() => watchlist.setModalOpen(true)}
                  onWatchlistDelete={watchlist.handleDelete}
                  portfolioRows={portfolio.rows}
                  portfolioLoading={portfolio.loading}
                  hasRealHoldings={portfolio.hasRealHoldings}
                  onPortfolioAdd={() => portfolio.setModalOpen(true)}
                  onPortfolioDelete={handleDeletePortfolioItem}
                  onPortfolioEdit={portfolio.openEdit}
                  marketStatus={marketStatus}
                />
                <div className="mt-4">
                  <EarningsCalendarCard />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Dashboard;
