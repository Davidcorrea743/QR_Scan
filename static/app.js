var LOGO_SRC = "/static/logo Dimsop_Isotipo";

function generateQR() {
  const text = document.getElementById("text").value;
  const canvas = document.getElementById("qrcode");
  const size = parseInt(document.getElementById("size").value) || 256;

  QRCode.toCanvas(
    canvas,
    text || "http://127.0.0.1:8000/scan",
    {
      width: size,
      margin: parseInt(document.getElementById("margin").value),
      color: {
        dark: document.getElementById("colorDark").value,
        light: document.getElementById("colorLight").value
      },
      errorCorrectionLevel: document.getElementById("ecLevel").value
    },
    function (error) {
      if (error) {
        console.error(error);
        return;
      }

      const ctx = canvas.getContext("2d");
      const logo = new Image();
      logo.src = LOGO_SRC;

      logo.onload = function () {
        const logoSize = size * 0.2;
        const x = (canvas.width - logoSize) / 2;
        const y = (canvas.height - logoSize) / 2;

        const padding = 8;
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(
          x - padding / 2,
          y - padding / 2,
          logoSize + padding,
          logoSize + padding
        );

        ctx.drawImage(logo, x, y, logoSize, logoSize);
      };
    }
  );
}

function downloadQR() {
  const canvas = document.getElementById("qrcode");

  if (!canvas || canvas.width === 0) {
    alert("Primero genera un código QR antes de descargarlo.");
    return;
  }

  try {
    const dataURL = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = dataURL;
    link.download = `codigo-qr-${new Date().getTime()}.png`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log("✅ QR descargado exitosamente");
  } catch (error) {
    console.error("Error al descargar QR:", error);
    alert("Error al descargar el código QR. Intenta de nuevo.");
  }
}
