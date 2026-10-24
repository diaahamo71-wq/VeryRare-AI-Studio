
use eframe::egui;
use std::path::PathBuf;

struct AudioTrack {
    sample_rate: u32,
    samples: Vec<[f32; 2]>,
}

struct VeryRareApp {
    vocal: Option<PathBuf>,
    music: Option<PathBuf>,
    prompt: String,
    vocal_volume: f32,
    music_volume: f32,
    warm: bool,
    reverb: bool,
    delay: bool,
    compressor: bool,
    status: String,
    styled: bool,
}

impl Default for VeryRareApp {
    fn default() -> Self {
        Self {
            vocal: None,
            music: None,
            prompt: String::from(
                "Dreamcore, warm soft vocal, gentle reverb"
            ),
            vocal_volume: 1.0,
            music_volume: 0.72,
            warm: true,
            reverb: true,
            delay: false,
            compressor: true,
            status: String::from("Ready to create your sound."),
            styled: false,
        }
    }
}

impl VeryRareApp {
    fn card<R>(
        ui: &mut egui::Ui,
        title: &str,
        add: impl FnOnce(&mut egui::Ui) -> R,
    ) -> R {
        egui::Frame::group(ui.style())
            .fill(egui::Color32::from_rgb(34, 27, 48))
            .show(ui, |ui| {
                ui.set_width(ui.available_width());
                ui.heading(
                    egui::RichText::new(title)
                        .color(egui::Color32::from_rgb(210, 190, 255)),
                );
                ui.add_space(8.0);
                add(ui)
            })
            .inner
    }

    fn choose_file() -> Option<PathBuf> {
        rfd::FileDialog::new()
            .add_filter("WAV audio", &["wav"])
            .pick_file()
    }

    fn read_wav(path: &PathBuf) -> Result<AudioTrack, String> {
        let mut reader = hound::WavReader::open(path)
            .map_err(|e| format!("Cannot open WAV: {e}"))?;

        let spec = reader.spec();
        let channels = spec.channels as usize;

        if channels == 0 || spec.sample_rate == 0 {
            return Err("Invalid audio format.".into());
        }

        let raw: Vec<f32> = match spec.sample_format {
            hound::SampleFormat::Float => reader
                .samples::<f32>()
                .map(|s| s.map_err(|e| e.to_string()))
                .collect::<Result<Vec<_>, _>>()?,

            hound::SampleFormat::Int => {
                let scale = 2_f32.powi(spec.bits_per_sample as i32 - 1);

                reader
                    .samples::<i32>()
                    .map(|s| {
                        s.map(|v| v as f32 / scale)
                            .map_err(|e| e.to_string())
                    })
                    .collect::<Result<Vec<_>, _>>()?
            }
        };

        let mut samples = Vec::with_capacity(raw.len() / channels);

        for frame in raw.chunks(channels) {
            if frame.len() != channels {
                break;
            }

            let left = frame[0];
            let right = if channels > 1 {
                frame[1]
            } else {
                left
            };

            samples.push([left, right]);
        }

        if samples.is_empty() {
            return Err("The selected WAV file is empty.".into());
        }

        Ok(AudioTrack {
            sample_rate: spec.sample_rate,
            samples,
        })
    }

    fn resample(
        input: &[[f32; 2]],
        old_rate: u32,
        new_rate: u32,
    ) -> Vec<[f32; 2]> {
        if old_rate == new_rate || input.len() < 2 {
            return input.to_vec();
        }

        let new_len =
            (input.len() as f64 * new_rate as f64 / old_rate as f64)
                .round() as usize;

        (0..new_len)
            .map(|i| {
                let position =
                    i as f64 * old_rate as f64 / new_rate as f64;

                let index = (position.floor() as usize)
                    .min(input.len() - 1);

                let next = (index + 1).min(input.len() - 1);
                let fraction = (position - index as f64) as f32;

                [
                    input[index][0] * (1.0 - fraction)
                        + input[next][0] * fraction,
                    input[index][1] * (1.0 - fraction)
                        + input[next][1] * fraction,
                ]
            })
            .collect()
    }

    fn apply_effects(&self, audio: &mut Vec<[f32; 2]>, rate: u32) {
        let dry = audio.clone();

        if self.warm {
            let mut previous = [0.0_f32; 2];
            let alpha = 0.72_f32;

            for frame in audio.iter_mut() {
                for channel in 0..2 {
                    previous[channel] =
                        alpha * previous[channel]
                        + (1.0 - alpha) * frame[channel];

                    frame[channel] =
                        frame[channel] * 0.65
                        + previous[channel] * 0.35;
                }
            }
        }

        if self.delay || self.reverb {
            let delay_samples = if self.delay {
                (rate as usize * 35 / 100).max(1)
            } else {
                (rate as usize * 11 / 100).max(1)
            };

            for i in delay_samples..audio.len() {
                for channel in 0..2 {
                    let amount = if self.delay { 0.18 } else { 0.08 };

                    audio[i][channel] +=
                        dry[i - delay_samples][channel] * amount;
                }
            }

            if self.reverb {
                for i in 0..audio.len() {
                    for channel in 0..2 {
                        let mut echo = 0.0;

                        for (ms, amount) in
                            [(70, 0.055), (130, 0.035), (210, 0.02)]
                        {
                            let offset = rate as usize * ms / 1000;

                            if i >= offset {
                                echo += dry[i - offset][channel] * amount;
                            }
                        }

                        audio[i][channel] += echo;
                    }
                }
            }
        }

        if self.compressor {
            for frame in audio.iter_mut() {
                for sample in frame.iter_mut() {
                    let x = *sample;

                    *sample = if x.abs() > 0.65 {
                        x.signum() * (0.65 + (x.abs() - 0.65) * 0.45)
                    } else {
                        x
                    };
                }
            }
        }
    }

    fn export_mix(&mut self) {
        let Some(vocal_path) = self.vocal.clone() else {
            self.status = "Please import your vocal WAV first.".into();
            return;
        };

        let Some(music_path) = self.music.clone() else {
            self.status = "Please import your instrumental WAV.".into();
            return;
        };

        let Some(output) = rfd::FileDialog::new()
            .set_file_name("VeryRare_Mix.wav")
            .add_filter("WAV audio", &["wav"])
            .save_file()
        else {
            return;
        };

        let result = (|| -> Result<(), String> {
            let mut vocal = Self::read_wav(&vocal_path)?;
            let music = Self::read_wav(&music_path)?;

            let rate = vocal.sample_rate;

            let mut vocal_samples = std::mem::take(&mut vocal.samples);
            self.apply_effects(&mut vocal_samples, rate);

            let music_samples =
                Self::resample(&music.samples, music.sample_rate, rate);

            let length = vocal_samples.len().max(music_samples.len());

            let mut mixed = vec![[0.0_f32; 2]; length];

            for i in 0..vocal_samples.len() {
                for ch in 0..2 {
                    mixed[i][ch] +=
                        vocal_samples[i][ch] * self.vocal_volume;
                }
            }

            for i in 0..music_samples.len() {
                for ch in 0..2 {
                    mixed[i][ch] +=
                        music_samples[i][ch] * self.music_volume;
                }
            }

            let peak = mixed
                .iter()
                .flat_map(|frame| frame.iter())
                .fold(0.0_f32, |p, x| p.max(x.abs()));

            if peak > 0.98 {
                let gain = 0.98 / peak;

                for frame in mixed.iter_mut() {
                    for sample in frame.iter_mut() {
                        *sample *= gain;
                    }
                }
            }

            let spec = hound::WavSpec {
                channels: 2,
                sample_rate: rate,
                bits_per_sample: 16,
                sample_format: hound::SampleFormat::Int,
            };

            let mut writer = hound::WavWriter::create(&output, spec)
                .map_err(|e| e.to_string())?;

            for frame in mixed {
                for sample in frame {
                    let value =
                        (sample.clamp(-1.0, 1.0) * i16::MAX as f32) as i16;

                    writer.write_sample(value)
                        .map_err(|e| e.to_string())?;
                }
            }

            writer.finalize().map_err(|e| e.to_string())?;
            Ok(())
        })();

        match result {
            Ok(()) => {
                self.status = format!(
                    "Mix exported successfully: {}",
                    output.display()
                );
            }
            Err(error) => {
                self.status = format!("Export failed: {error}");
            }
        }
    }

    fn apply_prompt(&mut self) {
        let p = self.prompt.to_lowercase();

        if p.contains("dreamcore") || p.contains("another world") {
            self.reverb = true;
            self.delay = true;
        }

        if p.contains("warm") || p.contains("soft") {
            self.warm = true;
        }

        if p.contains("natural") || p.contains("dry vocal") {
            self.reverb = false;
            self.delay = false;
        }

        if p.contains("compress") {
            self.compressor = true;
        }

        self.status =
            "Prompt matched to available controls. Review the settings."
                .into();
    }
}

impl eframe::App for VeryRareApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        if !self.styled {
            let mut style = (*ctx.style()).clone();

            style.visuals = egui::Visuals::dark();
            style.visuals.panel_fill =
                egui::Color32::from_rgb(23, 19, 33);
            style.visuals.window_fill =
                egui::Color32::from_rgb(29, 23, 42);
            style.visuals.widgets.inactive.bg_fill =
                egui::Color32::from_rgb(54, 41, 76);
            style.visuals.widgets.hovered.bg_fill =
                egui::Color32::from_rgb(104, 70, 155);
            style.visuals.widgets.active.bg_fill =
                egui::Color32::from_rgb(126, 87, 190);
            style.visuals.selection.bg_fill =
                egui::Color32::from_rgb(126, 87, 190);
            style.spacing.item_spacing = egui::vec2(10.0, 10.0);

            ctx.set_style(style);
            self.styled = true;
        }

        egui::CentralPanel::default()
            .frame(
                egui::Frame::none()
                    .fill(egui::Color32::from_rgb(23, 19, 33))
                    .inner_margin(20.0),
            )
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(
                        egui::RichText::new("✦ VeryRare")
                            .size(28.0)
                            .strong()
                            .color(egui::Color32::from_rgb(210, 190, 255)),
                    );

                    ui.label(
                        egui::RichText::new("AI STUDIO")
                            .small()
                            .color(egui::Color32::from_rgb(160, 143, 188)),
                    );

                    ui.with_layout(
                        egui::Layout::right_to_left(egui::Align::Center),
                        |ui| {
                            ui.label(
                                egui::RichText::new("LOCAL AUDIO")
                                    .small()
                                    .color(egui::Color32::from_rgb(155, 211, 174)),
                            );
                        },
                    );
                });

                ui.add_space(4.0);

                ui.label(
                    egui::RichText::new(
                        "Shape your voice. Build your atmosphere."
                    )
                    .color(egui::Color32::from_rgb(180, 164, 207)),
                );

                ui.add_space(18.0);

                ui.columns(2, |columns| {
                    Self::card(&mut columns[0], "01  VOCAL TRACK", |ui| {
                        ui.label("Your voice recording");

                        if ui.button("＋  Import Vocal WAV").clicked() {
                            if let Some(path) = Self::choose_file() {
                                self.vocal = Some(path);
                                self.status = "Vocal track selected.".into();
                            }
                        }

                        let name = self.vocal.as_ref()
                            .and_then(|p| p.file_name())
                            .and_then(|n| n.to_str())
                            .unwrap_or("No vocal selected");

                        ui.label(
                            egui::RichText::new(name)
                                .small()
                                .color(egui::Color32::from_rgb(190, 174, 220)),
                        );

                        ui.add(
                            egui::Slider::new(
                                &mut self.vocal_volume, 0.0..=1.5
                            )
                            .text("Vocal level"),
                        );
                    });

                    Self::card(&mut columns[1], "02  INSTRUMENTAL", |ui| {
                        ui.label("Your beat or instrumental");

                        if ui.button("＋  Import Instrumental").clicked() {
                            if let Some(path) = Self::choose_file() {
                                self.music = Some(path);
                                self.status = "Instrumental selected.".into();
                            }
                        }

                        let name = self.music.as_ref()
                            .and_then(|p| p.file_name())
                            .and_then(|n| n.to_str())
                            .unwrap_or("No instrumental selected");

                        ui.label(
                            egui::RichText::new(name)
                                .small()
                                .color(egui::Color32::from_rgb(190, 174, 220)),
                        );

                        ui.add(
                            egui::Slider::new(
                                &mut self.music_volume, 0.0..=1.5
                            )
                            .text("Music level"),
                        );
                    });
                });

                ui.add_space(12.0);

                Self::card(ui, "03  VOCAL ATMOSPHERE", |ui| {
                    ui.horizontal_wrapped(|ui| {
                        ui.checkbox(&mut self.warm, "Warm / Soft");
                        ui.checkbox(&mut self.reverb, "Reverb");
                        ui.checkbox(&mut self.delay, "Delay");
                        ui.checkbox(&mut self.compressor, "Compressor");
                    });

                    ui.add_space(5.0);

                    ui.label("Describe your desired sound");

                    ui.add(
                        egui::TextEdit::multiline(&mut self.prompt)
                            .desired_rows(2)
                            .hint_text(
                                "Dreamcore, distant echoes, warm intimate vocal..."
                            )
                            .desired_width(f32::INFINITY),
                    );

                    if ui.button("✦  Apply Prompt").clicked() {
                        self.apply_prompt();
                    }

                    ui.label(
                        egui::RichText::new(
                            "Prompt matching is rule-based in this version."
                        )
                        .small()
                        .color(egui::Color32::from_rgb(160, 143, 188)),
                    );
                });

                ui.add_space(14.0);

                ui.horizontal(|ui| {
                    if ui
                        .add_sized(
                            [200.0, 44.0],
                            egui::Button::new(
                                egui::RichText::new("Export Mixed WAV")
                                    .strong(),
                            ),
                        )
                        .clicked()
                    {
                        self.export_mix();
                    }

                    ui.label(
                        egui::RichText::new(&self.status)
                            .small()
                            .color(egui::Color32::from_rgb(190, 174, 220)),
                    );
                });

                ui.with_layout(
                    egui::Layout::bottom_up(egui::Align::Center),
                    |ui| {
                        ui.label(
                            egui::RichText::new(
                                "VERYRARE  •  MADE FOR YOUR SOUND"
                            )
                            .small()
                            .color(egui::Color32::from_rgb(119, 103, 145)),
                        );
                    },
                );
            });
    }
}

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1050.0, 760.0])
            .with_min_inner_size([850.0, 650.0]),
        ..Default::default()
    };

    eframe::run_native(
        "VeryRare AI Studio",
        options,
        Box::new(|_cc| Ok(Box::new(VeryRareApp::default()))),
    )
}
