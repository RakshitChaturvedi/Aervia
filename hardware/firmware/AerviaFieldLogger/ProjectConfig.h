#pragma once
// Optional local override; never put credentials in either configuration file.
#if __has_include("LocalConfig.h")
#include "LocalConfig.h"
#endif
#ifndef AERVIA_GOOGLE_SHEET_ID
#define AERVIA_GOOGLE_SHEET_ID ""
#endif
