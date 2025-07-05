//+------------------------------------------------------------------+
//| 🔱 Noctria Kingdom - EA Executor                                |
//| 🏛️ 命令実行専用EA（Veritas信号をもとに即時発注）              |
//+------------------------------------------------------------------+
#property strict

#include <stdlib.mqh>
#include <Trade\Trade.mqh>
#include <Files\File.mqh>
#include <stdlib.mqh>

input string SignalFileName = "veritas_signal.json";  // Filesディレクトリに置かれるシグナルファイル

CTrade trade;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("⚔️ Noctria Executor 起動: 命令を待機中...");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   string file_path = SignalFileName;
   if (!FileIsExist(file_path))
      return;

   int file_handle = FileOpen(file_path, FILE_READ | FILE_TXT | FILE_COMMON);
   if (file_handle == INVALID_HANDLE)
   {
      Print("⚠️ ファイルオープン失敗: ", file_path);
      return;
   }

   string json = FileReadString(file_handle);
   FileClose(file_handle);

   if (json == "")
      return;

   // 🔽 JSONから内容を抽出（超簡易パーサーで処理）
   string signal_type = ExtractJsonValue(json, "signal");
   string symbol      = ExtractJsonValue(json, "symbol");
   double lot         = StrToDouble(ExtractJsonValue(json, "lot"));
   double tp          = StrToDouble(ExtractJsonValue(json, "tp"));
   double sl          = StrToDouble(ExtractJsonValue(json, "sl"));

   // 🛒 注文実行
   if (signal_type == "BUY")
   {
      trade.Buy(lot, symbol, 0.0, 0.0, 0.0, "VeritasOrder");
      Print("🟢 BUY 発注: ", symbol);
   }
   else if (signal_type == "SELL")
   {
      trade.Sell(lot, symbol, 0.0, 0.0, 0.0, "VeritasOrder");
      Print("🔴 SELL 発注: ", symbol);
   }
   else
   {
      Print("⚠️ 不明なシグナルタイプ: ", signal_type);
   }

   // 📦 シグナルファイル削除（使い捨て処理）
   FileDelete(file_path);
}

//+------------------------------------------------------------------+
//| 簡易JSONパーサー                                                 |
//+------------------------------------------------------------------+
string ExtractJsonValue(string json, string key)
{
   string pattern = "\"" + key + "\":";
   int start = StringFind(json, pattern);
   if (start == -1)
      return "";

   start += StringLen(pattern);
   int end = StringFind(json, ",", start);
   if (end == -1)
      end = StringFind(json, "}", start);
   if (end == -1)
      return "";

   string value = StringSubstr(json, start, end - start);
   value = StringTrim(StringReplace(value, "\"", ""), " \r\n\t");
   return value;
}
