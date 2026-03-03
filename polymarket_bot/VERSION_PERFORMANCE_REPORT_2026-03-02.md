# Version Performance Report (Polymarket Bot)

**Generated:** 2026-03-02

## Attribution Method
- Version labels are assigned by trade timestamp using deployment checkpoints from today's run history.
- Checkpoints used (UTC):
  - v5.2 start: `2026-03-02T13:28:00+00:00`
  - v5.3 start: `2026-03-02T15:00:00+00:00`
- `v5.3+` includes v5.3 logic period; v5.3.1 was primarily UI-side.

## All-Time Closed Trade Snapshot
- Closed trades: **728**
- Realized PnL: **-88.59 USD**
- W/L: **329/398** (WR **45.3%**)

## Performance by Bot Version (timestamp-attributed)
| Version bucket | Closed trades | Wins | Losses | Win rate | Realized PnL |
|---|---:|---:|---:|---:|---:|
| <= v5.1 baseline | 674 | 284 | 389 | 42.2% | -193.63 |
| v5.2 | 27 | 22 | 5 | 81.5% | +40.73 |
| v5.3+ | 27 | 23 | 4 | 85.2% | +64.32 |

## Recent Closed Trades (latest 150), tagged by version bucket
| id | ts (UTC) | version bucket | slug | side | entry | close | reason | pnl_usd |
|---:|---|---|---|---|---:|---:|---|---:|
| 728 | 2026-03-02T16:06:32.690574+00:00 | v5.3+ | sol-updown-5m-1772467500 | BUY_YES | 0.4800 | 0.6500 | auto_take_profit | +3.42 |
| 727 | 2026-03-02T16:06:18.558333+00:00 | v5.3+ | btc-updown-5m-1772467500 | BUY_YES | 0.5000 | 0.6600 | auto_take_profit | +3.10 |
| 726 | 2026-03-02T16:01:26.366489+00:00 | v5.3+ | sol-updown-5m-1772467200 | BUY_YES | 0.4900 | 0.6400 | auto_take_profit | +2.87 |
| 725 | 2026-03-02T16:01:18.618500+00:00 | v5.3+ | btc-updown-5m-1772467200 | BUY_YES | 0.5100 | 0.3200 | auto_stop_loss | -2.01 |
| 724 | 2026-03-02T15:56:33.741930+00:00 | v5.3+ | sol-updown-5m-1772466900 | BUY_YES | 0.5000 | 0.6600 | auto_take_profit | +3.08 |
| 723 | 2026-03-02T15:56:25.863859+00:00 | v5.3+ | btc-updown-5m-1772466900 | BUY_YES | 0.5400 | 0.7000 | auto_take_profit | +2.72 |
| 722 | 2026-03-02T15:51:39.104617+00:00 | v5.3+ | sol-updown-5m-1772466600 | BUY_YES | 0.4800 | 0.6600 | auto_take_profit | +3.15 |
| 721 | 2026-03-02T15:51:18.109027+00:00 | v5.3+ | btc-updown-5m-1772466600 | BUY_YES | 0.5000 | 0.6500 | auto_take_profit | +2.74 |
| 720 | 2026-03-02T15:46:23.234945+00:00 | v5.3+ | sol-updown-5m-1772466300 | BUY_YES | 0.4900 | 0.3300 | auto_stop_loss | -1.69 |
| 719 | 2026-03-02T15:46:16.941288+00:00 | v5.3+ | btc-updown-5m-1772466300 | BUY_YES | 0.4400 | 0.5700 | auto_take_profit | +2.74 |
| 718 | 2026-03-02T15:41:31.495301+00:00 | v5.3+ | btc-updown-5m-1772466000 | BUY_YES | 0.4600 | 0.3600 | auto_stop_loss | -2.05 |
| 717 | 2026-03-02T15:41:19.415506+00:00 | v5.3+ | sol-updown-5m-1772466000 | BUY_YES | 0.4900 | 0.6500 | auto_take_profit | +3.13 |
| 716 | 2026-03-02T15:36:40.321016+00:00 | v5.3+ | sol-updown-5m-1772465700 | BUY_YES | 0.5100 | 0.6900 | auto_take_profit | +3.05 |
| 715 | 2026-03-02T15:36:19.551839+00:00 | v5.3+ | btc-updown-5m-1772465700 | BUY_YES | 0.4900 | 0.6500 | auto_take_profit | +2.79 |
| 714 | 2026-03-02T15:31:19.361357+00:00 | v5.3+ | btc-updown-5m-1772465400 | BUY_YES | 0.5000 | 0.6400 | auto_take_profit | +2.68 |
| 713 | 2026-03-02T15:26:22.521939+00:00 | v5.3+ | sol-updown-5m-1772465100 | BUY_YES | 0.4900 | 0.4600 | auto_stop_loss | -0.58 |
| 712 | 2026-03-02T15:26:16.065108+00:00 | v5.3+ | btc-updown-5m-1772465100 | BUY_YES | 0.4800 | 0.6200 | auto_take_profit | +2.79 |
| 711 | 2026-03-02T15:21:27.244236+00:00 | v5.3+ | sol-updown-5m-1772464800 | BUY_YES | 0.4800 | 0.6400 | auto_take_profit | +2.93 |
| 710 | 2026-03-02T15:21:20.698089+00:00 | v5.3+ | btc-updown-5m-1772464800 | BUY_YES | 0.5000 | 0.7000 | auto_take_profit | +3.47 |
| 709 | 2026-03-02T15:16:42.238867+00:00 | v5.3+ | sol-updown-5m-1772464500 | BUY_YES | 0.5500 | 0.7700 | auto_take_profit | +3.39 |
| 708 | 2026-03-02T15:16:30.120969+00:00 | v5.3+ | btc-updown-5m-1772464500 | BUY_YES | 0.4600 | 0.6500 | auto_take_profit | +3.40 |
| 707 | 2026-03-02T15:11:25.434475+00:00 | v5.3+ | sol-updown-5m-1772464200 | BUY_YES | 0.4800 | 0.6600 | auto_take_profit | +3.29 |
| 706 | 2026-03-02T15:11:19.057858+00:00 | v5.3+ | btc-updown-5m-1772464200 | BUY_YES | 0.4300 | 0.5800 | auto_take_profit | +3.03 |
| 705 | 2026-03-02T15:06:24.224469+00:00 | v5.3+ | sol-updown-5m-1772463900 | BUY_YES | 0.4800 | 0.6700 | auto_take_profit | +3.72 |
| 704 | 2026-03-02T15:06:17.952877+00:00 | v5.3+ | btc-updown-5m-1772463900 | BUY_YES | 0.4800 | 0.6200 | auto_take_profit | +2.51 |
| 703 | 2026-03-02T15:01:26.258864+00:00 | v5.3+ | sol-updown-5m-1772463600 | BUY_YES | 0.4800 | 0.6600 | auto_take_profit | +3.51 |
| 702 | 2026-03-02T15:01:19.675519+00:00 | v5.3+ | btc-updown-5m-1772463600 | BUY_YES | 0.4800 | 0.6400 | auto_take_profit | +3.13 |
| 701 | 2026-03-02T14:56:25.530913+00:00 | v5.2 | sol-updown-5m-1772463300 | BUY_YES | 0.4800 | 0.6200 | auto_take_profit | +2.54 |
| 700 | 2026-03-02T14:56:19.184799+00:00 | v5.2 | btc-updown-5m-1772463300 | BUY_YES | 0.4800 | 0.6200 | auto_take_profit | +2.54 |
| 699 | 2026-03-02T14:51:22.940939+00:00 | v5.2 | btc-updown-5m-1772463000 | BUY_YES | 0.4600 | 0.6400 | auto_take_profit | +3.29 |
| 698 | 2026-03-02T14:51:16.734215+00:00 | v5.2 | sol-updown-5m-1772463000 | BUY_YES | 0.4800 | 0.6200 | auto_take_profit | +2.73 |
| 697 | 2026-03-02T14:46:22.499886+00:00 | v5.2 | btc-updown-5m-1772462700 | BUY_YES | 0.4700 | 0.6100 | auto_take_profit | +2.77 |
| 696 | 2026-03-02T14:46:16.463996+00:00 | v5.2 | sol-updown-5m-1772462700 | BUY_YES | 0.4700 | 0.6400 | auto_take_profit | +3.36 |
| 695 | 2026-03-02T14:41:26.017747+00:00 | v5.2 | sol-updown-5m-1772462400 | BUY_YES | 0.4800 | 0.6400 | auto_take_profit | +2.75 |
| 694 | 2026-03-02T14:41:19.770746+00:00 | v5.2 | btc-updown-5m-1772462400 | BUY_YES | 0.4900 | 0.6600 | auto_take_profit | +3.21 |
| 693 | 2026-03-02T14:36:23.528762+00:00 | v5.2 | sol-updown-5m-1772462100 | BUY_YES | 0.4700 | 0.6400 | auto_take_profit | +2.96 |
| 692 | 2026-03-02T14:36:17.119009+00:00 | v5.2 | btc-updown-5m-1772462100 | BUY_YES | 0.4800 | 0.1900 | auto_stop_loss | -5.52 |
| 691 | 2026-03-02T14:32:28.638852+00:00 | v5.2 | btc-updown-5m-1772461800 | BUY_YES | 0.4800 | 0.6200 | auto_take_profit | +2.56 |
| 690 | 2026-03-02T14:31:29.542857+00:00 | v5.2 | sol-updown-5m-1772461800 | BUY_YES | 0.5100 | 0.7000 | auto_take_profit | +3.03 |
| 689 | 2026-03-02T14:26:31.025062+00:00 | v5.2 | btc-updown-5m-1772461500 | BUY_YES | 0.5500 | 0.7200 | auto_take_profit | +2.60 |
| 688 | 2026-03-02T14:26:19.415674+00:00 | v5.2 | sol-updown-5m-1772461500 | BUY_YES | 0.5000 | 0.6600 | auto_take_profit | +2.95 |
| 687 | 2026-03-02T14:21:34.877108+00:00 | v5.2 | sol-updown-5m-1772461200 | BUY_YES | 0.5100 | 0.6800 | auto_take_profit | +2.84 |
| 686 | 2026-03-02T14:21:17.058341+00:00 | v5.2 | btc-updown-5m-1772461200 | BUY_YES | 0.5000 | 0.6500 | auto_take_profit | +2.67 |
| 685 | 2026-03-02T14:16:33.595684+00:00 | v5.2 | sol-updown-5m-1772460900 | BUY_YES | 0.5100 | 0.6900 | auto_take_profit | +3.23 |
| 684 | 2026-03-02T14:16:27.504506+00:00 | v5.2 | btc-updown-5m-1772460900 | BUY_YES | 0.5000 | 0.6600 | auto_take_profit | +2.93 |
| 683 | 2026-03-02T14:12:52.218766+00:00 | v5.2 | btc-updown-5m-1772460600 | BUY_NO | 0.3900 | 0.2900 | auto_stop_loss | -2.32 |
| 682 | 2026-03-02T14:06:49.431501+00:00 | v5.2 | sol-updown-5m-1772460300 | BUY_NO | 0.3700 | 0.0100 | auto_stop_loss | -8.86 |
| 681 | 2026-03-02T14:06:43.750721+00:00 | v5.2 | btc-updown-5m-1772460300 | BUY_NO | 0.3400 | 0.0700 | auto_stop_loss | -7.23 |
| 680 | 2026-03-02T13:47:58.714353+00:00 | v5.2 | btc-updown-5m-1772459100 | BUY_NO | 0.3900 | 0.5700 | auto_take_profit | +4.25 |
| 679 | 2026-03-02T13:42:05.143691+00:00 | v5.2 | sol-updown-5m-1772458800 | BUY_NO | 0.3300 | 0.5300 | auto_take_profit | +5.55 |
| 678 | 2026-03-02T13:41:39.728561+00:00 | v5.2 | btc-updown-5m-1772458800 | BUY_NO | 0.3400 | 0.4600 | auto_take_profit | +3.26 |
| 677 | 2026-03-02T13:38:19.861592+00:00 | v5.2 | btc-updown-5m-1772458500 | BUY_NO | 0.3600 | 0.1900 | auto_stop_loss | -4.28 |
| 676 | 2026-03-02T13:31:22.239477+00:00 | v5.2 | sol-updown-5m-1772458200 | BUY_YES | 0.5300 | 0.7900 | auto_take_profit | +3.96 |
| 675 | 2026-03-02T13:31:16.686730+00:00 | v5.2 | btc-updown-5m-1772458200 | BUY_YES | 0.5300 | 0.7000 | auto_take_profit | +2.94 |
| 674 | 2026-03-02T13:26:21.900064+00:00 | <= v5.1 baseline | sol-updown-5m-1772457900 | BUY_YES | 0.4900 | 0.6500 | auto_take_profit | +2.98 |
| 673 | 2026-03-02T13:26:16.303270+00:00 | <= v5.1 baseline | btc-updown-5m-1772457900 | BUY_YES | 0.4900 | 0.6800 | auto_take_profit | +3.54 |
| 672 | 2026-03-02T13:21:23.050257+00:00 | <= v5.1 baseline | sol-updown-5m-1772457600 | BUY_YES | 0.4900 | 0.6800 | auto_take_profit | +3.11 |
| 671 | 2026-03-02T13:21:17.788109+00:00 | <= v5.1 baseline | btc-updown-5m-1772457600 | BUY_YES | 0.5200 | 0.6700 | auto_take_profit | +2.42 |
| 670 | 2026-03-02T13:16:20.904361+00:00 | <= v5.1 baseline | sol-updown-5m-1772457300 | BUY_YES | 0.5300 | 0.6800 | auto_take_profit | +2.49 |
| 669 | 2026-03-02T13:16:15.493741+00:00 | <= v5.1 baseline | btc-updown-5m-1772457300 | BUY_YES | 0.5400 | 0.7400 | auto_take_profit | +3.02 |
| 668 | 2026-03-02T13:11:25.960565+00:00 | <= v5.1 baseline | sol-updown-5m-1772457000 | BUY_YES | 0.5300 | 0.7600 | auto_take_profit | +3.91 |
| 667 | 2026-03-02T13:06:20.730939+00:00 | <= v5.1 baseline | sol-updown-5m-1772456700 | BUY_YES | 0.5300 | 0.6250 | expired_sweep_auto_close | +1.59 |
| 666 | 2026-03-02T13:06:16.441348+00:00 | <= v5.1 baseline | btc-updown-5m-1772456700 | BUY_YES | 0.5200 | 0.8050 | expired_sweep_auto_close | +4.87 |
| 665 | 2026-03-02T12:56:23.630275+00:00 | <= v5.1 baseline | sol-updown-5m-1772456100 | BUY_YES | 0.5100 | 0.3050 | expired_sweep_auto_close | -3.59 |
| 664 | 2026-03-02T12:56:19.191966+00:00 | <= v5.1 baseline | btc-updown-5m-1772456100 | BUY_YES | 0.5100 | 0.3250 | expired_sweep_auto_close | -3.24 |
| 663 | 2026-03-02T12:52:10.524040+00:00 | <= v5.1 baseline | sol-updown-5m-1772455800 | BUY_NO | 0.3800 | 0.2350 | expired_sweep_auto_close | -3.42 |
| 662 | 2026-03-02T12:52:02.604689+00:00 | <= v5.1 baseline | btc-updown-5m-1772455800 | BUY_NO | 0.3800 | 0.2550 | expired_sweep_auto_close | -2.95 |
| 661 | 2026-03-02T12:43:02.675891+00:00 | <= v5.1 baseline | btc-updown-5m-1772455200 | BUY_NO | 0.3500 | 0.6600 | expired_sweep_auto_close | +7.90 |
| 660 | 2026-03-02T12:27:00.863949+00:00 | <= v5.1 baseline | btc-updown-5m-1772454300 | BUY_NO | 0.3800 | 0.2600 | expired_sweep_auto_close | -2.82 |
| 659 | 2026-03-02T12:16:20.568037+00:00 | <= v5.1 baseline | sol-updown-5m-1772453700 | BUY_YES | 0.4800 | 0.1850 | expired_sweep_auto_close | -5.52 |
| 658 | 2026-03-02T12:16:16.633790+00:00 | <= v5.1 baseline | btc-updown-5m-1772453700 | BUY_YES | 0.5100 | 0.2650 | expired_sweep_auto_close | -4.31 |
| 657 | 2026-03-02T12:11:19.290518+00:00 | <= v5.1 baseline | sol-updown-5m-1772453400 | BUY_YES | 0.5000 | 0.6500 | expired_sweep_auto_close | +2.69 |
| 656 | 2026-03-02T12:11:15.368032+00:00 | <= v5.1 baseline | btc-updown-5m-1772453400 | BUY_YES | 0.5000 | 0.3950 | expired_sweep_auto_close | -1.89 |
| 655 | 2026-03-02T12:06:39.241321+00:00 | <= v5.1 baseline | sol-updown-5m-1772453100 | BUY_YES | 0.5000 | 0.3850 | expired_sweep_auto_close | -2.07 |
| 654 | 2026-03-02T12:06:17.406017+00:00 | <= v5.1 baseline | btc-updown-5m-1772453100 | BUY_YES | 0.5200 | 0.2850 | expired_sweep_auto_close | -4.07 |
| 653 | 2026-03-02T12:01:46.114877+00:00 | <= v5.1 baseline | sol-updown-5m-1772452800 | BUY_YES | 0.5400 | 0.4350 | expired_sweep_auto_close | -1.76 |
| 652 | 2026-03-02T12:01:17.050885+00:00 | <= v5.1 baseline | btc-updown-5m-1772452800 | BUY_YES | 0.4900 | 0.2000 | expired_sweep_auto_close | -5.35 |
| 651 | 2026-03-02T11:56:20.105738+00:00 | <= v5.1 baseline | sol-updown-5m-1772452500 | BUY_YES | 0.5000 | 0.4850 | expired_sweep_auto_close | -0.27 |
| 650 | 2026-03-02T11:56:16.152502+00:00 | <= v5.1 baseline | btc-updown-5m-1772452500 | BUY_YES | 0.5000 | 0.7550 | expired_sweep_auto_close | +4.60 |
| 649 | 2026-03-02T11:51:22.842176+00:00 | <= v5.1 baseline | sol-updown-5m-1772452200 | BUY_YES | 0.5000 | 0.5950 | expired_sweep_auto_close | +1.71 |
| 648 | 2026-03-02T11:51:15.554461+00:00 | <= v5.1 baseline | btc-updown-5m-1772452200 | BUY_YES | 0.4800 | 0.5650 | expired_sweep_auto_close | +1.59 |
| 647 | 2026-03-02T11:47:30.092092+00:00 | <= v5.1 baseline | sol-updown-5m-1772451900 | BUY_NO | 0.3900 | 0.0600 | expired_sweep_auto_close | -7.68 |
| 646 | 2026-03-02T11:46:50.550113+00:00 | <= v5.1 baseline | btc-updown-5m-1772451900 | BUY_NO | 0.3900 | 0.0750 | expired_sweep_auto_close | -7.33 |
| 645 | 2026-03-02T11:43:20.412254+00:00 | <= v5.1 baseline | btc-updown-5m-1772451600 | BUY_NO | 0.3800 | 0.2350 | expired_sweep_auto_close | -3.47 |
| 644 | 2026-03-02T11:36:59.874410+00:00 | <= v5.1 baseline | sol-updown-5m-1772451300 | BUY_NO | 0.3600 | 0.4950 | expired_sweep_auto_close | +3.40 |
| 643 | 2026-03-02T11:36:56.007678+00:00 | <= v5.1 baseline | btc-updown-5m-1772451300 | BUY_NO | 0.3700 | 0.4950 | expired_sweep_auto_close | +3.06 |
| 642 | 2026-03-02T11:31:19.519391+00:00 | <= v5.1 baseline | btc-updown-5m-1772451000 | BUY_YES | 0.5400 | 0.7050 | expired_sweep_auto_close | +2.76 |
| 641 | 2026-03-02T11:31:15.497773+00:00 | <= v5.1 baseline | sol-updown-5m-1772451000 | BUY_YES | 0.5000 | 0.6550 | expired_sweep_auto_close | +2.80 |
| 640 | 2026-03-02T11:26:41.005217+00:00 | <= v5.1 baseline | sol-updown-5m-1772450700 | BUY_YES | 0.5000 | 0.4950 | expired_sweep_auto_close | -0.09 |
| 639 | 2026-03-02T11:26:15.304449+00:00 | <= v5.1 baseline | btc-updown-5m-1772450700 | BUY_YES | 0.5200 | 0.5250 | expired_sweep_auto_close | +0.09 |
| 638 | 2026-03-02T11:22:39.665678+00:00 | <= v5.1 baseline | sol-updown-5m-1772450400 | BUY_NO | 0.3000 | 0.3600 | expired_sweep_auto_close | +1.80 |
| 637 | 2026-03-02T11:22:07.404459+00:00 | <= v5.1 baseline | btc-updown-5m-1772450400 | BUY_NO | 0.3100 | 0.5850 | expired_sweep_auto_close | +7.97 |
| 636 | 2026-03-02T11:16:47.438149+00:00 | <= v5.1 baseline | sol-updown-5m-1772450100 | BUY_NO | 0.3100 | 0.4950 | expired_sweep_auto_close | +5.34 |
| 635 | 2026-03-02T11:16:43.564677+00:00 | <= v5.1 baseline | btc-updown-5m-1772450100 | BUY_NO | 0.3000 | 0.4450 | expired_sweep_auto_close | +4.32 |
| 634 | 2026-03-02T11:12:10.924515+00:00 | <= v5.1 baseline | btc-updown-5m-1772449800 | BUY_NO | 0.3700 | 0.4050 | expired_sweep_auto_close | +0.85 |
| 633 | 2026-03-02T11:06:33.575027+00:00 | <= v5.1 baseline | sol-updown-5m-1772449500 | BUY_YES | 0.5100 | 0.4950 | expired_sweep_auto_close | -0.26 |
| 632 | 2026-03-02T11:06:18.914000+00:00 | <= v5.1 baseline | btc-updown-5m-1772449500 | BUY_YES | 0.5000 | 0.0450 | expired_sweep_auto_close | -8.17 |
| 631 | 2026-03-02T10:56:38.850241+00:00 | <= v5.1 baseline | sol-updown-5m-1772448900 | BUY_YES | 0.5000 | 0.4950 | expired_sweep_auto_close | -0.09 |
| 630 | 2026-03-02T10:56:16.603929+00:00 | <= v5.1 baseline | btc-updown-5m-1772448900 | BUY_YES | 0.5300 | 0.5250 | expired_sweep_auto_close | -0.08 |
| 629 | 2026-03-02T10:51:19.374719+00:00 | <= v5.1 baseline | sol-updown-5m-1772448600 | BUY_YES | 0.5000 | 0.1350 | expired_sweep_auto_close | -6.60 |
| 628 | 2026-03-02T10:51:15.483661+00:00 | <= v5.1 baseline | btc-updown-5m-1772448600 | BUY_YES | 0.5100 | 0.1450 | expired_sweep_auto_close | -6.47 |
| 627 | 2026-03-02T10:46:20.477191+00:00 | <= v5.1 baseline | sol-updown-5m-1772448300 | BUY_YES | 0.4800 | 0.3250 | expired_sweep_auto_close | -2.93 |
| 626 | 2026-03-02T10:46:16.101041+00:00 | <= v5.1 baseline | btc-updown-5m-1772448300 | BUY_YES | 0.5100 | 0.3550 | expired_sweep_auto_close | -2.76 |
| 625 | 2026-03-02T10:41:20.546868+00:00 | <= v5.1 baseline | sol-updown-5m-1772448000 | BUY_YES | 0.4900 | 0.1400 | expired_sweep_auto_close | -6.53 |
| 624 | 2026-03-02T10:41:16.499105+00:00 | <= v5.1 baseline | btc-updown-5m-1772448000 | BUY_YES | 0.4900 | 0.1450 | expired_sweep_auto_close | -6.43 |
| 623 | 2026-03-02T10:36:22.522574+00:00 | <= v5.1 baseline | sol-updown-5m-1772447700 | BUY_YES | 0.4800 | 0.2650 | expired_sweep_auto_close | -4.11 |
| 622 | 2026-03-02T10:36:18.615624+00:00 | <= v5.1 baseline | btc-updown-5m-1772447700 | BUY_YES | 0.5000 | 0.2750 | expired_sweep_auto_close | -4.13 |
| 621 | 2026-03-02T10:31:45.986045+00:00 | <= v5.1 baseline | sol-updown-5m-1772447400 | BUY_YES | 0.5900 | 0.5150 | expired_sweep_auto_close | -1.17 |
| 620 | 2026-03-02T10:31:16.418822+00:00 | <= v5.1 baseline | btc-updown-5m-1772447400 | BUY_YES | 0.5000 | 0.4950 | expired_sweep_auto_close | -0.09 |
| 619 | 2026-03-02T10:22:43.070421+00:00 | <= v5.1 baseline | btc-updown-5m-1772446800 | BUY_NO | 0.3700 | 0.1950 | expired_sweep_auto_close | -4.36 |
| 618 | 2026-03-02T10:16:56.427318+00:00 | <= v5.1 baseline | btc-updown-5m-1772446500 | BUY_NO | 0.3100 | 0.2950 | expired_sweep_auto_close | -0.45 |
| 617 | 2026-03-02T10:16:52.446038+00:00 | <= v5.1 baseline | sol-updown-5m-1772446500 | BUY_NO | 0.3900 | 0.4750 | expired_sweep_auto_close | +2.01 |
| 616 | 2026-03-02T10:07:21.900625+00:00 | <= v5.1 baseline | sol-updown-5m-1772445900 | BUY_NO | 0.3800 | 0.4650 | expired_sweep_auto_close | +2.06 |
| 615 | 2026-03-02T10:07:09.823910+00:00 | <= v5.1 baseline | btc-updown-5m-1772445900 | BUY_NO | 0.3800 | 0.3400 | expired_sweep_auto_close | -0.97 |
| 614 | 2026-03-02T10:03:18.353389+00:00 | <= v5.1 baseline | btc-updown-5m-1772445600 | BUY_NO | 0.3700 | 0.4600 | expired_sweep_auto_close | +2.23 |
| 613 | 2026-03-02T09:57:38.828397+00:00 | <= v5.1 baseline | btc-updown-5m-1772445300 | BUY_NO | 0.3900 | 0.6050 | expired_sweep_auto_close | +5.05 |
| 612 | 2026-03-02T09:46:19.579800+00:00 | <= v5.1 baseline | sol-updown-5m-1772444700 | BUY_YES | 0.5100 | 0.3350 | expired_sweep_auto_close | -3.15 |
| 611 | 2026-03-02T09:46:15.647619+00:00 | <= v5.1 baseline | btc-updown-5m-1772444700 | BUY_YES | 0.5100 | 0.3350 | expired_sweep_auto_close | -3.15 |
| 610 | 2026-03-02T09:41:41.465240+00:00 | <= v5.1 baseline | sol-updown-5m-1772444400 | BUY_YES | 0.4600 | 0.4050 | expired_sweep_auto_close | -1.10 |
| 609 | 2026-03-02T09:41:16.045969+00:00 | <= v5.1 baseline | btc-updown-5m-1772444400 | BUY_YES | 0.5000 | 0.3900 | expired_sweep_auto_close | -2.03 |
| 608 | 2026-03-02T09:36:20.587732+00:00 | <= v5.1 baseline | sol-updown-5m-1772444100 | BUY_YES | 0.5100 | 0.5050 | expired_sweep_auto_close | -0.09 |
| 607 | 2026-03-02T09:36:16.577401+00:00 | <= v5.1 baseline | btc-updown-5m-1772444100 | BUY_YES | 0.4900 | 0.5050 | expired_sweep_auto_close | +0.28 |
| 606 | 2026-03-02T09:31:20.315073+00:00 | <= v5.1 baseline | sol-updown-5m-1772443800 | BUY_YES | 0.4900 | 0.6450 | expired_sweep_auto_close | +2.90 |
| 605 | 2026-03-02T09:31:16.119913+00:00 | <= v5.1 baseline | btc-updown-5m-1772443800 | BUY_YES | 0.5100 | 0.6150 | expired_sweep_auto_close | +1.89 |
| 604 | 2026-03-02T09:26:21.059808+00:00 | <= v5.1 baseline | sol-updown-5m-1772443500 | BUY_YES | 0.4600 | 0.4450 | expired_sweep_auto_close | -0.30 |
| 603 | 2026-03-02T09:26:17.066483+00:00 | <= v5.1 baseline | btc-updown-5m-1772443500 | BUY_YES | 0.4300 | 0.1950 | expired_sweep_auto_close | -5.03 |
| 602 | 2026-03-02T09:21:19.064291+00:00 | <= v5.1 baseline | sol-updown-5m-1772443200 | BUY_YES | 0.4800 | 0.4850 | expired_sweep_auto_close | +0.10 |
| 601 | 2026-03-02T09:21:15.107795+00:00 | <= v5.1 baseline | btc-updown-5m-1772443200 | BUY_YES | 0.4000 | 0.5950 | expired_sweep_auto_close | +4.48 |
| 600 | 2026-03-02T09:16:22.391057+00:00 | <= v5.1 baseline | sol-updown-5m-1772442900 | BUY_YES | 0.4600 | 0.4150 | expired_sweep_auto_close | -0.90 |
| 599 | 2026-03-02T09:16:18.436913+00:00 | <= v5.1 baseline | btc-updown-5m-1772442900 | BUY_YES | 0.4800 | 0.6650 | expired_sweep_auto_close | +3.53 |
| 598 | 2026-03-02T09:11:20.585635+00:00 | <= v5.1 baseline | sol-updown-5m-1772442600 | BUY_YES | 0.5000 | 0.9250 | expired_sweep_auto_close | +7.74 |
| 597 | 2026-03-02T09:11:16.739021+00:00 | <= v5.1 baseline | btc-updown-5m-1772442600 | BUY_YES | 0.4600 | 0.7850 | expired_sweep_auto_close | +6.43 |
| 596 | 2026-03-02T09:06:21.993579+00:00 | <= v5.1 baseline | sol-updown-5m-1772442300 | BUY_YES | 0.4800 | 0.5350 | expired_sweep_auto_close | +1.04 |
| 595 | 2026-03-02T09:06:17.697756+00:00 | <= v5.1 baseline | btc-updown-5m-1772442300 | BUY_YES | 0.4700 | 0.4950 | expired_sweep_auto_close | +0.48 |
| 594 | 2026-03-02T09:01:19.400493+00:00 | <= v5.1 baseline | sol-updown-5m-1772442000 | BUY_YES | 0.4600 | 0.4750 | expired_sweep_auto_close | +0.30 |
| 593 | 2026-03-02T09:01:15.529972+00:00 | <= v5.1 baseline | btc-updown-5m-1772442000 | BUY_YES | 0.4400 | 0.4750 | expired_sweep_auto_close | +0.72 |
| 592 | 2026-03-02T08:56:22.738029+00:00 | <= v5.1 baseline | sol-updown-5m-1772441700 | BUY_YES | 0.4600 | 0.4550 | expired_sweep_auto_close | -0.10 |
| 591 | 2026-03-02T08:56:18.501101+00:00 | <= v5.1 baseline | btc-updown-5m-1772441700 | BUY_YES | 0.4300 | 0.4250 | expired_sweep_auto_close | -0.11 |
| 590 | 2026-03-02T08:51:22.482080+00:00 | <= v5.1 baseline | sol-updown-5m-1772441400 | BUY_YES | 0.4600 | 0.7750 | expired_sweep_auto_close | +6.18 |
| 589 | 2026-03-02T08:51:18.114984+00:00 | <= v5.1 baseline | btc-updown-5m-1772441400 | BUY_YES | 0.4700 | 0.8450 | expired_sweep_auto_close | +7.20 |
| 588 | 2026-03-02T08:46:20.242769+00:00 | <= v5.1 baseline | sol-updown-5m-1772441100 | BUY_YES | 0.4900 | 0.4800 | expired_sweep_auto_close | -0.18 |
| 587 | 2026-03-02T08:46:16.104935+00:00 | <= v5.1 baseline | btc-updown-5m-1772441100 | BUY_YES | 0.4800 | 0.4750 | expired_sweep_auto_close | -0.09 |
| 586 | 2026-03-02T08:41:40.583966+00:00 | <= v5.1 baseline | sol-updown-5m-1772440800 | BUY_YES | 0.4900 | 0.8450 | expired_sweep_auto_close | +6.50 |
| 585 | 2026-03-02T08:41:26.187631+00:00 | <= v5.1 baseline | btc-updown-5m-1772440800 | BUY_YES | 0.5000 | 0.7450 | expired_sweep_auto_close | +4.39 |
| 584 | 2026-03-02T08:37:07.486123+00:00 | <= v5.1 baseline | sol-updown-5m-1772440500 | BUY_NO | 0.3300 | 0.2950 | expired_sweep_auto_close | -0.95 |
| 583 | 2026-03-02T08:37:03.599119+00:00 | <= v5.1 baseline | btc-updown-5m-1772440500 | BUY_NO | 0.3800 | 0.3050 | expired_sweep_auto_close | -1.77 |
| 582 | 2026-03-02T08:32:21.240815+00:00 | <= v5.1 baseline | sol-updown-5m-1772440200 | BUY_NO | 0.3100 | 0.2050 | expired_sweep_auto_close | -3.05 |
| 581 | 2026-03-02T08:32:17.308896+00:00 | <= v5.1 baseline | btc-updown-5m-1772440200 | BUY_NO | 0.3800 | 0.2350 | expired_sweep_auto_close | -3.44 |
| 580 | 2026-03-02T08:27:00.460200+00:00 | <= v5.1 baseline | sol-updown-5m-1772439900 | BUY_NO | 0.3400 | 0.1650 | expired_sweep_auto_close | -4.66 |
| 579 | 2026-03-02T08:26:56.577879+00:00 | <= v5.1 baseline | btc-updown-5m-1772439900 | BUY_NO | 0.3400 | 0.2550 | expired_sweep_auto_close | -2.26 |