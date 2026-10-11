// Japanese OCR with Apple Vision. usage: ocr <image>... -> JSON list per image of {text, x, y, w, h, conf}
// Boxes are in pixels, origin top-left.
import Foundation
import Vision
import AppKit

var out: [String: [[String: Any]]] = [:]
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let W = Double(cg.width), H = Double(cg.height)
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["ja-JP"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    var items: [[String: Any]] = []
    for obs in req.results ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        items.append(["text": cand.string, "conf": cand.confidence,
                      "x": b.minX * W, "y": (1 - b.maxY) * H, "w": b.width * W, "h": b.height * H])
    }
    out[(path as NSString).lastPathComponent] = items
}
let data = try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(data)
