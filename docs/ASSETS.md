# The package tiles

*(Español: [ASSETS.es.md](ASSETS.es.md))*

The manifest names nine images, and **this repository ships none of them**: the ones in the real
package were made from the game's own artwork. You supply your own.

| File | Size |
|---|---|
| `Square150x150Logo.png` | 150 × 150 |
| `Square150x150Logo.scale-200.png` | 300 × 300 |
| `SplashScreen.png` | 620 × 300 |
| `SplashScreen.scale-200.png` | 1240 × 600 |
| `Square44x44Logo.png` | 44 × 44 |
| `Square44x44Logo.scale-200.png` | 88 × 88 |
| `Square44x44Logo.targetsize-24_altform-unplated.png` | 24 × 24 |
| `StoreLogo.png` | 50 × 50 |
| `StoreLogo.scale-200.png` | 100 × 100 |

PNG, 32-bit with alpha. The wide tile is not declared: the console never shows it.

`tools/acgc_mosaicos.py` generates plain placeholder tiles in the right sizes, which is enough to
get a package installed; replace them with your own art whenever you like.

Keep that art yours: screenshots, logos and character art from the game belong to their owners, and
a package that carries them is a package you cannot share.
